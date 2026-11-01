"""テストの共通部品（constitution 原則I：再現性の確認を中心にする。期待値との比較は行わない）

テストではネットワークを使わない。株価データ・決算発表は、決まった乱数の種から作った1時間足を DB に入れて使う。
yfinance・Alpha Vantage・Gemini は、呼ばれたら分かるように差し替える。
"""
import random
from datetime import date, datetime, time
from decimal import Decimal
from unittest import mock

import pytest

from hypotheses.models import Hypothesis
from marketdata.models import EarningsEvent, PriceBar
from marketdata.services import quarter_of
from marketdata.sessions import EASTERN, session_of, trading_days

# yfinance の1時間足の開始時刻（research 項目1。9:00 と 15:30 の足は30分）
BAR_TIMES = [time(h, 0) for h in range(4, 10)] + [time(h, 30) for h in range(9, 16)] + [time(h, 0) for h in range(16, 20)]

PERIOD_START = date(2026, 1, 5)
PERIOD_END = date(2026, 6, 30)
# 売却に使う、期間の後ろの数日分（simulation.services.SELL_LOOKAHEAD_DAYS より長く作る）
DATA_END = date(2026, 7, 15)
SYMBOLS = ['TSTA', 'TSTB']
AMOUNT = Decimal('10000')

FIXED_PROPOSALS = ['提案1', '提案2', '提案3']


def make_bars(symbol: str, start: date, end: date, seed: int) -> list[PriceBar]:
    """決まった乱数の種から、取引日ごとの1時間足を作る（同じ種なら常に同じ足になる）"""
    rng = random.Random(seed)
    price = Decimal('100')
    bars = []
    for day in trading_days(start, end):
        for bar_time in BAR_TIMES:
            timestamp = datetime.combine(day, bar_time, tzinfo=EASTERN)
            open_ = price
            close = (open_ * Decimal(str(1 + rng.uniform(-0.03, 0.03)))).quantize(Decimal('0.000001'))
            high = (max(open_, close) * Decimal(str(1 + rng.uniform(0, 0.02)))).quantize(Decimal('0.000001'))
            low = (min(open_, close) * Decimal(str(1 - rng.uniform(0, 0.02)))).quantize(Decimal('0.000001'))
            bars.append(PriceBar(
                symbol=symbol, timestamp=timestamp, open=open_, high=high, low=low, close=close,
                volume=0, session=session_of(timestamp),
            ))
            price = close
    return bars


def make_earnings(symbol: str, seed: int) -> list[EarningsEvent]:
    """検証期間の中の決算発表（市場前・市場中・市場後の発表を混ぜる）"""
    rng = random.Random(seed)
    events = []
    for month in (1, 2, 4, 5):
        day = trading_days(date(2026, month, 10), date(2026, month, 28))[rng.randrange(10)]
        announced_at = datetime.combine(day, rng.choice([time(7, 0), time(8, 0), time(12, 0), time(16, 0), time(16, 30)]), tzinfo=EASTERN)
        events.append(EarningsEvent(symbol=symbol, announced_at=announced_at, fiscal_quarter=quarter_of(announced_at)))
    return events


@pytest.fixture
def market_data(db):
    """検証期間とその後の数日分の株価データ・決算発表を DB に入れる"""
    for seed, symbol in enumerate(SYMBOLS, start=1):
        PriceBar.objects.bulk_create(make_bars(symbol, PERIOD_START, DATA_END, seed))
        EarningsEvent.objects.bulk_create(make_earnings(symbol, seed))


@pytest.fixture
def hypothesis(db):
    return Hypothesis.objects.create(
        text='テスト用の仮説',
        parsed={
            'trigger': {'type': 'earnings_prev_bar_close', 'quarter': None},
            'buy_percent': 1.0,
            'order_type': 'stop',
            'sell': {'type': 'session_last_bar'},
        },
    )


@pytest.fixture
def no_network():
    """yfinance と Alpha Vantage を差し替える。呼ばれたかどうかを、返す mock で確かめられる"""
    with mock.patch('marketdata.services.yf.Ticker') as ticker, \
            mock.patch('marketdata.services.urllib.request.urlopen') as urlopen:
        ticker.side_effect = AssertionError('yfinance が呼ばれました')
        urlopen.side_effect = AssertionError('Alpha Vantage が呼ばれました')
        yield ticker, urlopen


@pytest.fixture
def fixed_proposals():
    """Gemini の提案（FR-010-7）を決まった文章に差し替える。生成AIの提案は再現性の例外（原則IV）"""
    with mock.patch('simulation.services.propose_alternatives', return_value=FIXED_PROPOSALS) as proposals:
        yield proposals
