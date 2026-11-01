"""株価データ・決算発表データの取得と保存（research 項目1・2・6）

- DB にない期間だけ yfinance から取得し、保存済みのデータは上書きしない（原則IV）。
- 検証では、ここで保存したデータだけを使う。
"""
import logging
import math
from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pandas as pd
import yfinance as yf
from django.utils import timezone

from .models import EarningsEvent, PriceBar
from .sessions import EASTERN, session_of, to_eastern

logger = logging.getLogger(__name__)

# yfinance の1時間足は直近730日以内しか取得できない（research 項目1）
MAX_HISTORY_DAYS = 729

# 決算発表の時刻が取れない場合にみなす時刻（FR-014）
ASSUMED_PRE_MARKET_TIME = time(8, 0)
ASSUMED_POST_MARKET_TIME = time(16, 0)

# 最後に保存した決算発表から、次の発表があり得るまでの日数（約1四半期）
EARNINGS_REFRESH_DAYS = 100


class MarketDataError(Exception):
    """yfinance からの取得に失敗した"""


def quarter_of(announced_at: datetime) -> int:
    """暦年で数えた四半期。1〜3月の発表が第1四半期（FR-025）"""
    return (to_eastern(announced_at).month - 1) // 3 + 1


def ensure_market_data(symbol: str, start: date, end: date) -> None:
    """検証期間（start〜end、両端を含む）の株価データと決算発表データを、DB になければ取得して保存する"""
    ensure_price_bars(symbol, start, end)
    ensure_earnings_events(symbol, start, end)


# ---------- 株価データ（1時間足） ----------

def ensure_price_bars(symbol: str, start: date, end: date) -> int:
    """DB にない期間の1時間足だけを取得して保存し、新しく保存した本数を返す"""
    today = timezone.now().astimezone(EASTERN).date()
    start = max(start, today - timedelta(days=MAX_HISTORY_DAYS))
    end = min(end, today)
    if start > end:
        return 0

    saved = 0
    for fetch_start, fetch_end in _missing_ranges(symbol, start, end):
        saved += _save_price_bars(symbol, _download_price_bars(symbol, fetch_start, fetch_end))
    return saved


def _missing_ranges(symbol: str, start: date, end: date) -> list[tuple[date, date]]:
    """保存済みの最初の足より前、最後の足より後で、平日を含む期間を返す。途中の欠けは取り直さない"""
    bars = PriceBar.objects.filter(symbol=symbol)
    first = bars.order_by('timestamp').first()
    if first is None:
        return [(start, end)]

    last = bars.order_by('-timestamp').first()
    first_day = to_eastern(first.timestamp).date()
    last_day = to_eastern(last.timestamp).date()

    ranges = []
    if start < first_day and _has_weekday(start, first_day - timedelta(days=1)):
        ranges.append((start, first_day - timedelta(days=1)))
    if end > last_day and _has_weekday(last_day + timedelta(days=1), end):
        ranges.append((last_day + timedelta(days=1), end))
    return ranges


def _has_weekday(start: date, end: date) -> bool:
    day = start
    while day <= end:
        if day.weekday() < 5:
            return True
        day += timedelta(days=1)
    return False


def _download_price_bars(symbol: str, start: date, end: date) -> pd.DataFrame:
    """yfinance から1時間足を取得する（市場前・市場後を含み、株式分割などで調整しない価格）"""
    try:
        return yf.Ticker(symbol).history(
            start=datetime.combine(start, time(0, 0), tzinfo=EASTERN),
            end=datetime.combine(end + timedelta(days=1), time(0, 0), tzinfo=EASTERN),
            interval='1h',
            prepost=True,
            auto_adjust=False,
        )
    except Exception as e:
        raise MarketDataError(f'{symbol} の株価データを取得できませんでした: {e}') from e


def _save_price_bars(symbol: str, df: pd.DataFrame) -> int:
    rows = []
    for ts, row in df.iterrows():
        prices = [row['Open'], row['High'], row['Low'], row['Close']]
        if any(_is_missing(p) for p in prices):
            continue
        timestamp = ts.to_pydatetime()
        rows.append(PriceBar(
            symbol=symbol,
            timestamp=timestamp,
            open=_to_decimal(row['Open']),
            high=_to_decimal(row['High']),
            low=_to_decimal(row['Low']),
            close=_to_decimal(row['Close']),
            volume=0 if _is_missing(row['Volume']) else int(row['Volume']),
            session=session_of(timestamp),
        ))
    before = PriceBar.objects.filter(symbol=symbol).count()
    # 同じ銘柄・同じ日時のデータがすでにある場合は、上書きせずに飛ばす
    PriceBar.objects.bulk_create(rows, ignore_conflicts=True)
    return PriceBar.objects.filter(symbol=symbol).count() - before


def _is_missing(value) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def _to_decimal(value) -> Decimal:
    return Decimal(str(round(float(value), 6)))


# ---------- 決算発表 ----------

def ensure_earnings_events(symbol: str, start: date, end: date) -> int:
    """決算発表が DB にない、または最後の発表から約1四半期が過ぎている場合だけ取得して保存し、新しく保存した件数を返す"""
    today = timezone.now().astimezone(EASTERN).date()
    latest = EarningsEvent.objects.filter(symbol=symbol).order_by('-announced_at').first()
    if latest is not None:
        next_possible = to_eastern(latest.announced_at).date() + timedelta(days=EARNINGS_REFRESH_DAYS)
        if next_possible > min(end, today):
            return 0
    return _save_earnings_events(symbol, _download_earnings_dates(symbol))


def _download_earnings_dates(symbol: str) -> pd.DataFrame:
    try:
        df = yf.Ticker(symbol).get_earnings_dates(limit=25)
    except Exception as e:
        raise MarketDataError(f'{symbol} の決算発表データを取得できませんでした: {e}') from e
    return df if df is not None else pd.DataFrame()


def _save_earnings_events(symbol: str, df: pd.DataFrame) -> int:
    saved = 0
    for ts, row in df.iterrows():
        # 発表済み（実際の EPS がある）回だけを使う（research 項目2）
        if _is_missing(row.get('Reported EPS')):
            continue
        announced_at = resolve_announced_at(ts.to_pydatetime())
        if announced_at is None:
            logger.warning('%s %s の決算発表は時刻が分からないため保存しません', symbol, ts)
            continue
        day = announced_at.date()
        # 同じ日の決算発表がすでにある場合は、上書きせずに飛ばす
        exists = any(
            to_eastern(e.announced_at).date() == day
            for e in EarningsEvent.objects.filter(
                symbol=symbol,
                announced_at__range=(announced_at - timedelta(days=1), announced_at + timedelta(days=1)),
            )
        )
        if exists:
            continue
        EarningsEvent.objects.create(
            symbol=symbol,
            announced_at=announced_at,
            fiscal_quarter=quarter_of(announced_at),
        )
        saved += 1
    return saved


def resolve_announced_at(raw: datetime, timing: str | None = None) -> datetime | None:
    """発表日時を決める。時刻が取れない場合は、区分（市場前／市場後）から時刻をみなす（FR-014）

    yfinance は時刻付きで返すが、時刻がない（0:00）場合に区分も分からなければ None を返す。
    """
    eastern = to_eastern(raw)
    if eastern.time() != time(0, 0):
        return eastern
    if timing == 'pre':
        return datetime.combine(eastern.date(), ASSUMED_PRE_MARKET_TIME, tzinfo=EASTERN)
    if timing == 'post':
        return datetime.combine(eastern.date(), ASSUMED_POST_MARKET_TIME, tzinfo=EASTERN)
    return None
