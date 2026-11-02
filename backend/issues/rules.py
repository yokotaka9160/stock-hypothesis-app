"""問題点の判定（FR-010-1〜FR-010-4、FR-010-6）

決まったルールで判定する。DB には触れず、シミュレーションの結果だけから判定する。
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from simulation.engine import SymbolSimulation, totals

from .models import Issue

# FR-010-2・3：1回の取引あたりの損益が購入金額の -10% 以下
LOSS_RATE_THRESHOLD = Decimal('-0.10')
# FR-010-4：総取引回数がこの回数以下
FEW_TRADES_THRESHOLD = 2


@dataclass(frozen=True)
class IssueFinding:
    aspect: str
    reason: str


def judge_issues(simulations: list[SymbolSimulation], amount: Decimal) -> list[IssueFinding]:
    """問題点を、時間帯・トリガー条件・トリガー条件の数値・取引回数の順に返す。問題がなければ空"""
    findings = []
    total = totals(simulations)

    # FR-010-1：夜間（20:00〜翌4:00）に取引が行われる
    night_symbols = [s.symbol for s in simulations if s.night_trade]
    if night_symbols:
        findings.append(IssueFinding(
            Issue.ASPECT_TIME_OF_DAY,
            f'夜間（米国東部時間 20:00〜翌4:00）に購入する取引があります（{"、".join(night_symbols)}）。'
            '夜間の価格データは取れないため、この銘柄は検証不可になりました。',
        ))

    # FR-010-2・3：全銘柄合計の損益 ÷（購入金額 × 総取引回数）が -10% 以下。0回なら判定しない
    if total.trade_count > 0:
        rate = total.pnl / (amount * total.trade_count)
        if rate <= LOSS_RATE_THRESHOLD:
            rate_text = f'{(rate * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)}%'
            findings.append(IssueFinding(
                Issue.ASPECT_TRIGGER,
                f'1回の取引あたりの損益が、購入金額の {rate_text} です（-10% 以下）。'
                'トリガー条件（決算発表の前の足で買う）が、この銘柄・期間では利益につながっていない可能性があります。',
            ))
            findings.append(IssueFinding(
                Issue.ASPECT_TRIGGER_VALUE,
                f'1回の取引あたりの損益が、購入金額の {rate_text} です（-10% 以下）。'
                '購入条件の %（トリガーの足の終値からどれだけ離れた価格で買うか）が合っていない可能性があります。',
            ))

    # FR-010-4：総取引回数が2回以下（0回を含む）
    if total.trade_count <= FEW_TRADES_THRESHOLD:
        findings.append(IssueFinding(
            Issue.ASPECT_TRADE_COUNT,
            f'総取引回数が {total.trade_count} 回です（2回以下）。'
            '回数が少ないため、結果がたまたまである可能性があります。銘柄を増やすなどして確かめてください。',
        ))
    return findings
