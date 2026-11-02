"""改善案：時間帯・トリガー（FR-010-7、research 項目7）

Gemini に仮説と検証結果を渡し、別の時間帯またはトリガー条件の案を3個、文章で返させる。
提案は再検証しない。生成AIの提案なので、同じ条件でも内容は毎回変わり得る（原則IV の例外）。
Gemini が失敗した場合（無料枠の上限・60秒応答なしなど）は GeminiError を出し、呼び出し側で検証全体を失敗にする。
"""
from decimal import Decimal

from .client import GeminiError, generate_json

PROPOSAL_COUNT = 3

# 未検証である旨と、過学習の注意書き（FR-010-7、FR-010-8）
UNVERIFIED_NOTE = (
    'この提案は生成AIによるもので、再検証していません（未検証）。'
    '検証するには、提案をもとに仮説を保存して検証してください。'
    'また、過去のデータにたまたま合った考えである可能性（過学習）にも注意してください。'
)

RESPONSE_SCHEMA = {
    'type': 'object',
    'properties': {
        'proposals': {'type': 'array', 'items': {'type': 'string'}},
    },
    'required': ['proposals'],
}

PROMPT = """あなたは米国株の売買の仮説を見直す助言役です。
次の仮説と、過去の株価データでのシミュレーション結果をもとに、
「取引を実行する時間帯」または「トリガー条件」を変えた別の仮説の案を、ちょうど{count}個提案してください。

# 守ること
- 日本語で書く。1つの案は2〜3文で、変える内容と、そう考える理由を書く
- 購入条件の %（数値）だけを変える案は出さない（数値の改善案は別に計算している）
- 出来高を使う案は出さない（市場前・市場後の出来高のデータがないため）
- 時間帯は米国東部時間で、市場前 4:00〜9:30、市場中 9:30〜16:00、市場後 16:00〜20:00、夜間 20:00〜翌4:00
- 結果を断定せず、案として書く

# 仮説の文章
{text}

# 読み取った条件
- トリガー条件：{trigger}
- 購入条件：トリガーの1時間足の終値から {percent}% の価格
- 購入方法：{order_type}
- 売却条件：購入が市場前・市場後なら、市場前の最後の1時間足の終値で全売却。購入が市場中なら、市場中の最後の1時間足の終値で全売却

# シミュレーション結果
- 銘柄：{symbols}
- 検証期間：{period_start}〜{period_end}
- 購入金額（1回の取引あたり）：{amount} 米ドル
- 総取引回数：{trade_count} 回
- 損益額（全銘柄合計）：{pnl} 米ドル
- 購入した時間帯ごとの取引回数：{sessions}
- 見つかった問題点：{issues}
"""

ORDER_TYPE_LABELS = {'stop': '逆指値', 'limit': '指値'}
SESSION_LABELS = {'pre': '市場前', 'regular': '市場中', 'post': '市場後', 'night': '夜間'}


def propose_alternatives(
    text: str,
    parsed: dict,
    symbols: list[str],
    period_start,
    period_end,
    amount: Decimal,
    trade_count: int,
    pnl: Decimal,
    session_counts: dict[str, int],
    issue_reasons: list[str],
) -> list[str]:
    """時間帯・トリガーの改善案を3個返す"""
    quarter = parsed['trigger'].get('quarter')
    trigger = (
        f'第{quarter}四半期の' if quarter else '（すべての四半期の）'
    ) + '決算発表時刻を含む1時間足の、1本前の1時間足が確定したとき'
    prompt = PROMPT.format(
        count=PROPOSAL_COUNT,
        text=text,
        trigger=trigger,
        percent=parsed['buy_percent'],
        order_type=ORDER_TYPE_LABELS.get(parsed['order_type'], parsed['order_type']),
        symbols='、'.join(symbols),
        period_start=period_start,
        period_end=period_end,
        amount=amount,
        trade_count=trade_count,
        pnl=pnl.quantize(Decimal('0.01')),
        sessions='、'.join(f'{SESSION_LABELS[k]} {v} 回' for k, v in session_counts.items()) or 'なし',
        issues=' / '.join(issue_reasons) or 'なし',
    )
    result = generate_json(prompt, RESPONSE_SCHEMA)
    proposals = [p.strip() for p in result.get('proposals', []) if isinstance(p, str) and p.strip()]
    if len(proposals) < PROPOSAL_COUNT:
        raise GeminiError(f'Gemini の提案が{PROPOSAL_COUNT}個に足りませんでした。もう一度検証してください')
    return proposals[:PROPOSAL_COUNT]
