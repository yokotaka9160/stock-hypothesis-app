"""時間帯（市場前／市場中／市場後／夜間）の判定（FR-016、research 項目4）

時刻はすべて米国東部時間（America/New_York）に変換してから判定する。
タイムゾーン付きの時刻で扱うので、夏時間・冬時間の切り替えは自動で反映される。
"""
from datetime import datetime, time
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo('America/New_York')

PRE_MARKET = 'pre'
REGULAR = 'regular'
POST_MARKET = 'post'
NIGHT = 'night'

SESSION_CHOICES = [
    (PRE_MARKET, '市場前'),
    (REGULAR, '市場中'),
    (POST_MARKET, '市場後'),
    (NIGHT, '夜間'),
]

PRE_MARKET_START = time(4, 0)
REGULAR_START = time(9, 30)
POST_MARKET_START = time(16, 0)
POST_MARKET_END = time(20, 0)


def to_eastern(dt: datetime) -> datetime:
    """タイムゾーン付きの時刻を米国東部時間に変換する"""
    if dt.tzinfo is None:
        raise ValueError('タイムゾーンのない時刻は扱えません')
    return dt.astimezone(EASTERN)


def session_of(dt: datetime) -> str:
    """時刻が属する時間帯を返す。1時間足は足の開始時刻で判定する（FR-016）"""
    t = to_eastern(dt).time()
    if PRE_MARKET_START <= t < REGULAR_START:
        return PRE_MARKET
    if REGULAR_START <= t < POST_MARKET_START:
        return REGULAR
    if POST_MARKET_START <= t < POST_MARKET_END:
        return POST_MARKET
    return NIGHT
