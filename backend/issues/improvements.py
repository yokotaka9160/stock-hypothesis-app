"""改善案：数値（FR-010-5）

購入条件の % を -15% から +15% まで 1% 刻み（31通り）で再検証し、全銘柄合計の損益が一番良い1つを返す。
問題点の有無にかかわらず常に出す。再検証は、元の検証と同じ1時間足・決算発表だけで行う（原則IV）。
"""
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from hypotheses.parser import ORDER_LIMIT, ORDER_STOP
from simulation.engine import Totals

PERCENT_RANGE = range(-15, 16)

# 過学習の注意書き（FR-010-8）
OVERFITTING_NOTE = (
    'この改善案は、過去のデータにたまたま合った結果である可能性があります（過学習）。'
    '別の期間や銘柄でも同じ結果になるかを確かめてから使ってください。'
)


@dataclass(frozen=True)
class NumericImprovement:
    buy_percent: Decimal
    order_type: str
    totals: Totals


def order_type_for(percent: int) -> str:
    """再検証での購入方法。プラスは逆指値、0% とマイナスは指値（FR-010-5。この再検証にだけ使う）"""
    return ORDER_STOP if percent > 0 else ORDER_LIMIT


def find_numeric_improvement(parsed: dict, simulate: Callable[[dict], Totals]) -> NumericImprovement:
    """31通りを再検証して、一番良い1つを返す

    simulate は、読み取り結果（parsed）を受け取り、全銘柄合計を返す関数。
    損益が同じなら元の % に一番近いもの、それも同じなら % が小さいものを選ぶ。
    """
    original = Decimal(str(parsed['buy_percent']))
    candidates = []
    for percent in PERCENT_RANGE:
        variant = {**parsed, 'buy_percent': percent, 'order_type': order_type_for(percent)}
        candidates.append(NumericImprovement(Decimal(percent), order_type_for(percent), simulate(variant)))
    return min(
        candidates,
        key=lambda c: (-c.totals.pnl, abs(c.buy_percent - original), c.buy_percent),
    )
