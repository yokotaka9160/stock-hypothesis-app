"""検証の実行（データ取得 → シミュレーション → 問題点 → 改善案 → 保存）（FR-004〜FR-011）

検証には DB に保存したデータだけを使う。DB にないデータだけを先に yfinance から取得する（原則IV）。
Gemini による改善案（FR-010-7）が失敗した場合は、検証全体を失敗とし、結果は保存しない。
"""
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from advisor.client import GeminiError
from advisor.proposals import UNVERIFIED_NOTE, propose_alternatives
from hypotheses.models import Hypothesis
from issues.improvements import OVERFITTING_NOTE, NumericImprovement, find_numeric_improvement
from issues.models import Improvement, Issue
from issues.rules import IssueFinding, judge_issues
from marketdata.models import EarningsEvent, PriceBar
from marketdata.services import MarketDataError, ensure_market_data
from marketdata.sessions import EASTERN

from .engine import Bar, EarningsAnnouncement, SymbolSimulation, simulate_symbol, totals
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
    # 元の検証と改善案の再検証で、同じデータを使う
    inputs = {
        symbol: (
            _load_bars(symbol, period_start, period_end + timedelta(days=SELL_LOOKAHEAD_DAYS)),
            _load_announcements(symbol, period_start, period_end),
        )
        for symbol in symbols
    }

    def simulate_all(parsed: dict) -> list[SymbolSimulation]:
        return [
            simulate_symbol(symbol, parsed, bars, announcements, period_start, period_end, amount, today)
            for symbol, (bars, announcements) in inputs.items()
        ]

    simulations = simulate_all(run.hypothesis_parsed)
    total = totals(simulations)
    findings = judge_issues(simulations, amount)
    numeric = find_numeric_improvement(run.hypothesis_parsed, lambda parsed: totals(simulate_all(parsed)))

    try:
        proposals = propose_alternatives(
            run.hypothesis_text,
            run.hypothesis_parsed,
            symbols,
            period_start,
            period_end,
            amount,
            total.trade_count,
            total.pnl,
            _session_counts(simulations),
            [f.reason for f in findings],
        )
    except GeminiError as e:
        # Gemini の失敗（無料枠の上限・60秒応答なしなど）は、検証全体の失敗とする（FR-010-7）
        run.error_message = str(e)
        run.save(update_fields=['error_message'])
        return run

    with transaction.atomic():
        for simulation in simulations:
            _save_simulation(run, simulation)
        _save_issues_and_improvements(run, findings, numeric, proposals)
        run.status = VerificationRun.STATUS_SUCCESS
        run.save(update_fields=['status'])
    return run


def _session_counts(simulations: list[SymbolSimulation]) -> dict[str, int]:
    """購入した時間帯ごとの取引回数（検証不可の銘柄は除く）"""
    counts: dict[str, int] = {}
    for simulation in simulations:
        if simulation.unavailable:
            continue
        for trade in simulation.trades:
            counts[trade.buy_session] = counts.get(trade.buy_session, 0) + 1
    return counts


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


def _save_issues_and_improvements(
    run: VerificationRun,
    findings: list[IssueFinding],
    numeric: NumericImprovement,
    proposals: list[str],
) -> None:
    """問題点と改善案を保存する。改善案は、関係する問題点があればそれに結び付ける"""
    issues = {}
    for position, finding in enumerate(findings):
        issues[finding.aspect] = Issue.objects.create(
            run=run, aspect=finding.aspect, reason=finding.reason, position=position
        )

    percent = numeric.buy_percent
    percent_text = f'{percent:+}' if percent != 0 else '0'
    order_label = '逆指値' if numeric.order_type == 'stop' else '指値'
    Improvement.objects.create(
        run=run,
        issue=issues.get(Issue.ASPECT_TRIGGER_VALUE),
        kind=Improvement.KIND_NUMERIC,
        proposal=f'購入条件を、トリガーの1時間足の終値から {percent_text}% の価格（{order_label}）にする',
        buy_percent=percent,
        order_type=numeric.order_type,
        result_pnl=numeric.totals.pnl,
        result_trade_count=numeric.totals.trade_count,
        note=OVERFITTING_NOTE,
        position=0,
    )
    ai_issue = issues.get(Issue.ASPECT_TRIGGER) or issues.get(Issue.ASPECT_TIME_OF_DAY)
    Improvement.objects.bulk_create([
        Improvement(
            run=run,
            issue=ai_issue,
            kind=Improvement.KIND_AI,
            proposal=proposal,
            note=UNVERIFIED_NOTE,
            position=position,
        )
        for position, proposal in enumerate(proposals, start=1)
    ])
