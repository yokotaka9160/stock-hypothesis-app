"""再現性のテスト（T034・T035。FR-011、SC-002、原則I・IV）

同じ条件で2回検証し、結果が完全に一致することを確かめる。期待値との比較は行わない。
"""
from unittest import mock

from issues import improvements
from simulation.models import VerificationRun
from simulation.services import run_verification

from .conftest import AMOUNT, PERIOD_END, PERIOD_START, SYMBOLS


def snapshot(run: VerificationRun) -> dict:
    """検証結果のうち、実行ごとに変わる id・実行日時・AI の提案を除いたすべて"""
    return {
        'status': run.status,
        'error_message': run.error_message,
        'symbol_results': [
            {
                'symbol': r.symbol,
                'trade_count': r.trade_count,
                'pnl': r.pnl,
                'unavailable': r.unavailable,
                'missing_dates': r.missing_dates,
                'trades': list(r.trades.order_by('buy_at').values(
                    'buy_at', 'buy_price', 'buy_session', 'order_type', 'quantity', 'sell_at', 'sell_price', 'pnl',
                )),
            }
            for r in run.symbol_results.order_by('symbol')
        ],
        'issues': list(run.issues.values('aspect', 'reason', 'position')),
        'numeric_improvement': list(run.improvements.filter(kind='numeric').values(
            'proposal', 'buy_percent', 'order_type', 'result_pnl', 'result_trade_count', 'note',
        )),
    }


def verify(hypothesis):
    return run_verification(hypothesis, SYMBOLS, PERIOD_START, PERIOD_END, AMOUNT)


def test_same_conditions_give_identical_results(market_data, hypothesis, no_network, fixed_proposals):
    """T034：同じ条件で2回検証すると、結果が完全に一致する（FR-011）"""
    first = verify(hypothesis)
    second = verify(hypothesis)

    assert first.status == VerificationRun.STATUS_SUCCESS
    assert first.pk != second.pk
    assert snapshot(first) == snapshot(second)


def test_same_conditions_give_identical_results_for_limit_order_and_quarter(
    market_data, hypothesis, no_network, fixed_proposals,
):
    """T034：購入方法が指値で、四半期を指定した仮説でも、2回の結果が完全に一致する"""
    hypothesis.parsed = {**hypothesis.parsed, 'buy_percent': -1.5, 'order_type': 'limit',
                         'trigger': {'type': 'earnings_prev_bar_close', 'quarter': 2}}
    hypothesis.save()

    assert snapshot(verify(hypothesis)) == snapshot(verify(hypothesis))


def test_numeric_improvement_rechecks_are_identical(market_data, hypothesis, no_network, fixed_proposals):
    """T035：改善案（31通り）の再検証結果が、2回とも一致する（FR-010-5）"""
    real = improvements.find_numeric_improvement
    recorded: list[list] = []

    def recording(parsed, simulate):
        results = []

        def simulate_and_record(variant):
            totals = simulate(variant)
            results.append((variant['buy_percent'], variant['order_type'], totals.trade_count, totals.pnl))
            return totals

        chosen = real(parsed, simulate_and_record)
        recorded.append(results)
        return chosen

    with mock.patch('simulation.services.find_numeric_improvement', side_effect=recording):
        first = verify(hypothesis)
        second = verify(hypothesis)

    assert len(recorded) == 2
    assert len(recorded[0]) == len(improvements.PERCENT_RANGE)
    assert recorded[0] == recorded[1]
    assert snapshot(first)['numeric_improvement'] == snapshot(second)['numeric_improvement']
