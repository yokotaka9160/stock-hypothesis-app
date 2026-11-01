"""シミュレーションの計算（FR-004a、FR-004b、FR-007〜FR-009、FR-016、FR-025）

DB には触れず、渡された1時間足と決算発表だけから計算する。同じ入力なら常に同じ結果になる（原則IV）。
金額・価格はすべて Decimal で計算する。
"""
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from hypotheses.parser import ORDER_LIMIT, ORDER_STOP
from marketdata.sessions import (
    NIGHT,
    PRE_MARKET,
    REGULAR,
    next_trading_day,
    session_of,
    to_eastern,
    trading_days,
)

PRICE_STEP = Decimal('0.000001')

# 市場中の最後の1時間足（15:30〜16:00）と、市場前の最後の1時間足（9:00〜9:30）の開始時刻（FR-008b、research 項目1）
REGULAR_LAST_BAR = time(15, 30)
PRE_MARKET_LAST_BAR = time(9, 0)
# 時間帯の境目。1時間足はこの時刻で区切られる（9:00 と 15:30 の足は30分）
SESSION_BOUNDARIES = (time(9, 30), time(16, 0), time(20, 0))


@dataclass(frozen=True)
class Bar:
    start: datetime  # 足の開始日時（米国東部時間）
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(frozen=True)
class EarningsAnnouncement:
    announced_at: datetime
    quarter: int


@dataclass(frozen=True)
class SimulatedTrade:
    buy_at: datetime
    buy_price: Decimal
    buy_session: str
    order_type: str
    quantity: int
    sell_at: datetime
    sell_price: Decimal
    pnl: Decimal


@dataclass
class SymbolSimulation:
    symbol: str
    unavailable: bool = False
    # 夜間に購入する取引があった（FR-009 で検証不可、FR-010-1 で問題点）
    night_trade: bool = False
    trades: list[SimulatedTrade] = field(default_factory=list)
    missing_dates: list[date] = field(default_factory=list)

    @property
    def trade_count(self) -> int:
        return len(self.trades)

    @property
    def pnl(self) -> Decimal:
        return sum((t.pnl for t in self.trades), Decimal('0'))


@dataclass(frozen=True)
class Totals:
    trade_count: int
    pnl: Decimal


def bar_end(start: datetime) -> datetime:
    """足の終了日時。時間帯の境目をまたぐ場合は境目で終わる（9:00 と 15:30 の足は30分）"""
    end = start + timedelta(hours=1)
    for boundary in SESSION_BOUNDARIES:
        b = datetime.combine(start.date(), boundary, tzinfo=start.tzinfo)
        if start < b < end:
            return b
    return end


def fill_price(order_type: str, bar: Bar, order_price: Decimal) -> Decimal | None:
    """買い注文の約定価格。約定しなければ None（FR-008a）"""
    if order_type == ORDER_STOP:
        if bar.open > order_price:
            return bar.open
        if bar.high >= order_price:
            return order_price
        return None
    if order_type == ORDER_LIMIT:
        if bar.open < order_price:
            return bar.open
        if bar.low <= order_price:
            return order_price
        return None
    raise ValueError(f'購入方法が正しくありません: {order_type}')


def simulate_symbol(
    symbol: str,
    parsed: dict,
    bars: list[Bar],
    announcements: list[EarningsAnnouncement],
    period_start: date,
    period_end: date,
    amount: Decimal,
    today: date,
) -> SymbolSimulation:
    """1銘柄の検証期間をシミュレーションする

    bars は検証期間と、その後の売却に使う数日分の1時間足（米国東部時間）。
    today より後の日は、まだデータがない日として「欠けている日」には含めない。
    """
    result = SymbolSimulation(symbol)
    bars_by_day: dict[date, list[Bar]] = {}
    for bar in sorted(bars, key=lambda b: b.start):
        bars_by_day.setdefault(bar.start.date(), []).append(bar)

    period_days = trading_days(period_start, min(period_end, today))
    if not any(day in bars_by_day for day in period_days):
        # 銘柄の全日データが取れなければ検証不可（FR-009）
        result.unavailable = True
        return result
    missing = {day for day in period_days if day not in bars_by_day}

    quarter = parsed['trigger'].get('quarter')
    buy_percent = Decimal(str(parsed['buy_percent']))
    order_type = parsed['order_type']
    position_until: datetime | None = None

    for announcement in sorted(announcements, key=lambda a: a.announced_at):
        announced_at = to_eastern(announcement.announced_at)
        if not (period_start <= announced_at.date() <= period_end):
            continue
        if quarter is not None and announcement.quarter != quarter:
            continue

        day_bars = bars_by_day.get(announced_at.date())
        if not day_bars:
            continue
        # 決算発表時刻を含む1時間足。なければトリガーは成立しない（例：20:00 以降の発表）
        index = next(
            (i for i, b in enumerate(day_bars) if b.start <= announced_at < bar_end(b.start)),
            None,
        )
        # 1本前の足は同じ日の足に限る（FR-025）
        if index is None or index == 0:
            continue
        trigger_bar, order_bar = day_bars[index - 1], day_bars[index]
        if bar_end(trigger_bar.start) != order_bar.start:
            # 1本前の足のデータが欠けている
            missing.add(announced_at.date())
            continue

        trigger_at = order_bar.start  # 1本前の足が確定した時刻
        if position_until is not None and trigger_at < position_until:
            # 保有中・注文の有効時間中のトリガーは無視する（FR-004b）
            continue

        order_price = (trigger_bar.close * (Decimal('100') + buy_percent) / Decimal('100')).quantize(
            PRICE_STEP, rounding=ROUND_HALF_UP
        )
        # 注文の有効時間は60分。1時間足では、トリガーの次の1本の足だけを有効とする（FR-008）
        position_until = bar_end(order_bar.start)
        buy_price = fill_price(order_type, order_bar, order_price)
        if buy_price is None:
            continue
        quantity = int(amount // buy_price)
        if quantity == 0:
            continue  # 1株も買えない場合は購入しなかったものとする（FR-004a）

        buy_session = session_of(order_bar.start)
        if buy_session == NIGHT:
            # 夜間の価格データは取れないので検証不可（FR-009）
            result.unavailable = True
            result.night_trade = True
            return result

        sell_bar, sell_day = _find_sell_bar(order_bar, buy_session, bars_by_day)
        if sell_bar is None:
            # 売却する足のデータが欠けている場合は、購入しなかったものとする（FR-008b）
            if sell_day <= today:
                missing.add(sell_day)
            continue

        result.trades.append(SimulatedTrade(
            buy_at=order_bar.start,
            buy_price=buy_price,
            buy_session=buy_session,
            order_type=order_type,
            quantity=quantity,
            sell_at=sell_bar.start,
            sell_price=sell_bar.close,
            pnl=(sell_bar.close - buy_price) * quantity,
        ))
        position_until = bar_end(sell_bar.start)

    result.missing_dates = sorted(missing)
    return result


def _find_sell_bar(order_bar: Bar, buy_session: str, bars_by_day: dict[date, list[Bar]]) -> tuple[Bar | None, date]:
    """売却する足（FR-008b）。購入が市場中なら当日の市場中の最後の足、
    市場前なら当日の、市場後なら翌営業日の、市場前の最後の足。同じ足で売却のタイミングが来たらその足で売る
    """
    buy_day = order_bar.start.date()
    if buy_session == REGULAR:
        sell_day, sell_time = buy_day, REGULAR_LAST_BAR
    elif buy_session == PRE_MARKET:
        sell_day, sell_time = buy_day, PRE_MARKET_LAST_BAR
    else:
        sell_day, sell_time = next_trading_day(buy_day), PRE_MARKET_LAST_BAR
    for bar in bars_by_day.get(sell_day, []):
        if bar.start.time() == sell_time and bar.start >= order_bar.start:
            return bar, sell_day
    return None, sell_day


def totals(results: list[SymbolSimulation]) -> Totals:
    """全銘柄合計。検証不可の銘柄は含めない（FR-007）"""
    available = [r for r in results if not r.unavailable]
    return Totals(
        trade_count=sum(r.trade_count for r in available),
        pnl=sum((r.pnl for r in available), Decimal('0')),
    )
