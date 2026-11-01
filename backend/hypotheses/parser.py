"""仮説の文章を Gemini で読み取り、検証できる範囲（FR-025）かどうかを確認する（FR-017、FR-018、research 項目5）

読み取り結果（parsed）の形:
    {
        "trigger": {"type": "earnings_prev_bar_close", "quarter": 1},  # quarter は 1〜4、指定なしは null
        "buy_percent": 4.0,          # トリガーの1時間足の終値から何 % の価格で買うか（マイナスは下の価格）
        "order_type": "stop",        # "stop"（逆指値）または "limit"（指値）
        "sell": {"type": "session_last_bar"},
    }
トリガー条件と売却条件は FR-025 で1種類ずつに決まっているので、種類（とトリガーの対象の四半期）だけを持つ。
"""
import math

from advisor.client import generate_json

# FR-025：決算発表時刻を含む1時間足の、1本前の1時間足が確定したとき（対象の四半期は任意）
TRIGGER_EARNINGS = 'earnings_prev_bar_close'
QUARTERS = (1, 2, 3, 4)
# FR-025：市場前・市場後に買ったら市場前の最後の1時間足、市場中に買ったら市場中の最後の1時間足の終値で全売却
SELL_SESSION_LAST_BAR = 'session_last_bar'

ORDER_STOP = 'stop'
ORDER_LIMIT = 'limit'
ORDER_TYPES = (ORDER_STOP, ORDER_LIMIT)

ITEM_TRIGGER = 'トリガー条件'
ITEM_BUY = '購入条件'
ITEM_ORDER = '購入方法'
ITEM_SELL = '売却条件'


class HypothesisParseError(Exception):
    """文章を読み取れなかった、または検証できる範囲外だった（FR-018、FR-025）"""

    def __init__(
        self,
        message: str,
        missing_items: list[str] | None = None,
        suggestion: dict | None = None,
    ):
        super().__init__(message)
        self.missing_items = missing_items or []
        # 範囲に合うように補った文章の提案（FR-026）。{"text": ..., "note": ...}
        self.suggestion = suggestion


PROMPT = """あなたは株式売買の仮説を、決まった形式に読み取る係です。
次の「仮説の文章」を読み、各項目が以下の「検証できる範囲」に当てはまるかを判定してください。
推測で補わず、文章に書かれていない項目は当てはまらないものとしてください。

# 検証できる範囲
- トリガー条件：決算発表時刻を含む1時間足の、1本前の1時間足が確定したとき
  （この意味と同じ場合だけ trigger_ok を true にする。「決算発表の5分前」など別の条件は false）
  対象の四半期は任意。「第1四半期」〜「第4四半期」のように1つ指定されていれば trigger_quarter にその数字（1〜4）を、
  指定がなければ null を入れる。四半期の指定がなくても trigger_ok は false にしない
- 購入条件：トリガーの1時間足の終値から、指定した % の価格
  （上昇・上の価格はプラス、下落・下の価格はマイナス、終値ちょうどは 0。% が書かれていなければ null）
- 購入方法：逆指値（stop）または指値（limit）。書かれていなければ unknown
- 売却条件：市場前・市場後に買った場合は市場前の最後の1時間足の終値で全売却、
  市場中に買った場合は市場中の最後の1時間足の終値で全売却
  （この意味と同じ場合だけ sell_ok を true にする）

# 範囲外だった場合の提案
1つでも当てはまらない項目がある場合は、元の文章の内容（数値・購入方法・言い回し）をできるだけ保ちながら、
すべての項目が上の範囲に当てはまるように補った仮説の文章を suggested_text に書いてください。
トリガー条件と売却条件は、次の文をそのまま含めてください（言い換えたり、一部だけにしたりしないこと）。
- トリガー条件：「{trigger_sentence}」（元の文章で四半期が指定されている場合は、文の前に「第N四半期の」を付ける）
- 売却条件：「{sell_sentence}」
元の文章に書かれていない項目を補った場合や、範囲に合わせて変えた場合は、何をどう補った・変えたかを
suggestion_note に短く書いてください。すべての項目が当てはまる場合は、どちらも null にしてください。

# 仮説の文章
{text}
"""

# 提案に、そのまま含める文（FR-025）
TRIGGER_SENTENCE = '決算発表時刻を含む1時間足の、1本前の1時間足が確定したときに'
SELL_SENTENCE = (
    '市場前・市場後に買った場合は市場前の最後の1時間足の終値で全売却し、'
    '市場中に買った場合は市場中の最後の1時間足の終値で全売却する'
)

RESPONSE_SCHEMA = {
    'type': 'object',
    'properties': {
        'trigger_ok': {'type': 'boolean'},
        'trigger_quarter': {'type': 'integer', 'nullable': True},
        'buy_percent': {'type': 'number', 'nullable': True},
        'order_type': {'type': 'string', 'enum': ['stop', 'limit', 'unknown']},
        'sell_ok': {'type': 'boolean'},
        'suggested_text': {'type': 'string', 'nullable': True},
        'suggestion_note': {'type': 'string', 'nullable': True},
    },
    'required': ['trigger_ok', 'trigger_quarter', 'buy_percent', 'order_type', 'sell_ok'],
}


def parse_hypothesis(text: str) -> dict:
    """文章を読み取り、parsed を返す。読み取れない・範囲外の場合は HypothesisParseError を出す

    Gemini の失敗（無料枠の上限・60秒応答なしなど）は advisor.client の例外がそのまま出る。
    """
    if not text or not text.strip():
        raise HypothesisParseError('仮説の文章を入力してください')
    prompt = PROMPT.format(text=text.strip(), trigger_sentence=TRIGGER_SENTENCE, sell_sentence=SELL_SENTENCE)
    result = generate_json(prompt, RESPONSE_SCHEMA)
    if not isinstance(result, dict):
        raise HypothesisParseError('仮説の文章を読み取れませんでした')

    missing = []
    quarter = result.get('trigger_quarter')
    if isinstance(quarter, float) and quarter.is_integer():
        quarter = int(quarter)
    if result.get('trigger_ok') is not True or not _is_valid_quarter(quarter):
        missing.append(ITEM_TRIGGER)
    buy_percent = result.get('buy_percent')
    if not _is_valid_percent(buy_percent):
        missing.append(ITEM_BUY)
    order_type = result.get('order_type')
    if order_type not in ORDER_TYPES:
        missing.append(ITEM_ORDER)
    if result.get('sell_ok') is not True:
        missing.append(ITEM_SELL)
    if missing:
        raise HypothesisParseError(
            '次の項目を、検証できる範囲で読み取れませんでした。文章を修正してください：' + '、'.join(missing),
            missing,
            _suggestion(result),
        )

    return _build(quarter, float(buy_percent), order_type)


def _suggestion(result: dict) -> dict | None:
    text = result.get('suggested_text')
    if not isinstance(text, str) or not text.strip():
        return None
    note = result.get('suggestion_note')
    return {'text': text.strip(), 'note': note.strip() if isinstance(note, str) and note.strip() else None}


def validate_parsed(parsed) -> dict:
    """保存前に、読み取り結果の形を確認して整える。書き換えられるのは % と購入方法だけ（FR-021）"""
    if not isinstance(parsed, dict):
        raise HypothesisParseError('読み取り結果の形が正しくありません')
    trigger = parsed.get('trigger') or {}
    if trigger.get('type') != TRIGGER_EARNINGS or not _is_valid_quarter(trigger.get('quarter')):
        raise HypothesisParseError('トリガー条件が検証できる範囲外です', [ITEM_TRIGGER])
    if (parsed.get('sell') or {}).get('type') != SELL_SESSION_LAST_BAR:
        raise HypothesisParseError('売却条件が検証できる範囲外です', [ITEM_SELL])
    buy_percent = parsed.get('buy_percent')
    if not _is_valid_percent(buy_percent):
        raise HypothesisParseError('購入条件の % が正しくありません', [ITEM_BUY])
    order_type = parsed.get('order_type')
    if order_type not in ORDER_TYPES:
        raise HypothesisParseError('購入方法は逆指値か指値を選んでください', [ITEM_ORDER])
    return _build(trigger.get('quarter'), float(buy_percent), order_type)


def _is_valid_percent(value) -> bool:
    # bool は int の一種なので除く。-100% 以下は価格が0以下になるため除く
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value > -100
    )


def _is_valid_quarter(value) -> bool:
    """対象の四半期は 1〜4、または指定なし（None）"""
    return value is None or (isinstance(value, int) and not isinstance(value, bool) and value in QUARTERS)


def _build(quarter: int | None, buy_percent: float, order_type: str) -> dict:
    return {
        'trigger': {'type': TRIGGER_EARNINGS, 'quarter': quarter},
        'buy_percent': buy_percent,
        'order_type': order_type,
        'sell': {'type': SELL_SESSION_LAST_BAR},
    }
