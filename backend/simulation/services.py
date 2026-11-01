"""検証の実行（データ取得 → シミュレーション → 保存）（FR-004〜FR-009、FR-011）

検証には DB に保存したデータだけを使う。DB にないデータだけを先に yfinance から取得する（原則IV）。
問題点の判定と改善案（Phase 5）は、シミュレーションの後に加える。
"""
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from hypotheses.models import Hypothesis
from marketdata.models import EarningsEvent, PriceBar
from marketdata.services import MarketDataError, ensure_market_data
from marketdata.sessions import EASTERN

from .engine import Bar, EarningsAnnouncement, SymbolSimulation, simulate_symbol
from .models import SymbolResult, Trade, VerificationRun

# 検証期間の最終日に市場後で買った場合でも売却できるよう、期間の後ろに余分に読み込む日数
SELL_LOOKAHEAD_DAYS = 7


def run_verification(
    hypothesis: Hypothesis,
    symbols: list[str],
    period_start: date,
    period_end: date,
    amount: Decimal,
) -> VerificationRun:
    """検証を実行して保存し、VerificationRun を返す。失敗した場合も、エラー文を付けて保存する"""
    run = VerificationRun.objects.create(
        hypothesis=hypothesis,
        hypothesis_text=hypothesis.text,
        hypothesis_parsed=hypothesis.parsed,
        symbols=symbols,
        period_start=period_start,
        period_end=period_end,
        amount=amount,
        status=VerificationRun.STATUS_FAILED,
    )
    try:
        for symbol in symbols:
            ensure_market_data(symbol, period_start, period_end + timedelta(days=SELL_LOOKAHEAD_DAYS))
    except MarketDataError as e:
        run.error_message = str(e)
        run.save(update_fields=['error_message'])
        return run

    today = timezone.now().astimezone(EASTERN).date()
    simulations = [
        simulate_symbol(
            symbol,
            run.hypothesis_parsed,
            _load_bars(symbol, period_start, period_end + timedelta(days=SELL_LOOKAHEAD_DAYS)),
            _load_announcements(symbol, period_start, period_end),
            period_start,
            period_end,
            amount,
            today,
        )
        for symbol in symbols
    ]

    with transaction.atomic():
        for simulation in simulations:
            _save_simulation(run, simulation)
        run.status = VerificationRun.STATUS_SUCCESS
        run.save(update_fields=['status'])
    return run


def _load_bars(symbol: str, start: date, end: date) -> list[Bar]:
    rows = PriceBar.objects.filter(
        symbol=symbol,
        timestamp__gte=datetime.combine(start, time(0, 0), tzinfo=EASTERN),
        timestamp__lt=datetime.combine(end + timedelta(days=1), time(0, 0), tzinfo=EASTERN),
    ).order_by('timestamp')
    return [
        Bar(start=r.timestamp.astimezone(EASTERN), open=r.open, high=r.high, low=r.low, close=r.close)
        for r in rows
    ]


def _load_announcements(symbol: str, start: date, end: date) -> list[EarningsAnnouncement]:
    rows = EarningsEvent.objects.filter(
        symbol=symbol,
        announced_at__gte=datetime.combine(start, time(0, 0), tzinfo=EASTERN),
        announced_at__lt=datetime.combine(end + timedelta(days=1), time(0, 0), tzinfo=EASTERN),
    ).order_by('announced_at')
    return [EarningsAnnouncement(announced_at=r.announced_at, quarter=r.fiscal_quarter) for r in rows]


def _save_simulation(run: VerificationRun, simulation: SymbolSimulation) -> None:
    result = SymbolResult.objects.create(
        run=run,
        symbol=simulation.symbol,
        trade_count=simulation.trade_count,
        pnl=simulation.pnl,
        unavailable=simulation.unavailable,
        missing_dates=[d.isoformat() for d in simulation.missing_dates],
    )
    Trade.objects.bulk_create([
        Trade(
            result=result,
            buy_at=t.buy_at,
            buy_price=t.buy_price,
            buy_session=t.buy_session,
            order_type=t.order_type,
            quantity=t.quantity,
            sell_at=t.sell_at,
            sell_price=t.sell_price,
            pnl=t.pnl,
        )
        for t in simulation.trades
    ])
