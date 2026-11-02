"""保存したデータのテスト（T036・T037。原則IV、research 項目6）

- 保存済みの株価データ・決算発表は上書きされない
- データが揃っていれば、検証中に yfinance・Alpha Vantage を呼ばず、DB のデータだけを使う
"""
from datetime import datetime, time, timedelta

import pandas as pd

from marketdata import services
from marketdata.models import EarningsEvent, PriceBar
from marketdata.sessions import EASTERN
from simulation.models import VerificationRun
from simulation.services import run_verification

from .conftest import AMOUNT, PERIOD_END, PERIOD_START, SYMBOLS

PRICE_FIELDS = ('symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume', 'session', 'fetched_at')
EARNINGS_FIELDS = ('symbol', 'announced_at', 'fiscal_quarter', 'fetched_at')


def stored_prices() -> list[dict]:
    return list(PriceBar.objects.order_by('symbol', 'timestamp').values(*PRICE_FIELDS))


def stored_earnings() -> list[dict]:
    return list(EarningsEvent.objects.order_by('symbol', 'announced_at').values(*EARNINGS_FIELDS))


def test_saved_price_bars_are_not_overwritten(market_data):
    """T036：同じ銘柄・同じ日時の足を、違う価格でもう一度保存しても、保存済みの足は変わらない"""
    symbol = SYMBOLS[0]
    existing = list(PriceBar.objects.filter(symbol=symbol).order_by('timestamp')[:5])
    before = stored_prices()

    # 保存済みの5本（価格を変えたもの）と、まだない1本
    new_timestamp = existing[-1].timestamp + timedelta(days=400)
    index = pd.DatetimeIndex([b.timestamp for b in existing] + [new_timestamp])
    df = pd.DataFrame(
        {'Open': 1.0, 'High': 2.0, 'Low': 0.5, 'Close': 1.5, 'Volume': 999},
        index=index,
    )
    saved = services._save_price_bars(symbol, df)

    assert saved == 1
    after = stored_prices()
    added = [row for row in after if row not in before]
    assert len(added) == 1 and added[0]['timestamp'] == new_timestamp
    assert [row for row in after if row in before] == before


def test_saved_earnings_events_are_not_overwritten(market_data, no_network):
    """T036：同じ日の決算発表を、違う時刻でもう一度保存しても、保存済みの決算発表は変わらない"""
    symbol = SYMBOLS[0]
    event = EarningsEvent.objects.filter(symbol=symbol).first()
    before = stored_earnings()

    other_time = datetime.combine(event.announced_at.astimezone(EASTERN).date(), time(10, 0), tzinfo=EASTERN)
    df = pd.DataFrame({'Reported EPS': [1.23]}, index=pd.DatetimeIndex([other_time]))
    saved = services._save_earnings_events(symbol, df)

    assert saved == 0
    assert stored_earnings() == before


def test_verification_does_not_change_saved_data(market_data, hypothesis, no_network, fixed_proposals):
    """T036：検証を実行しても、保存済みの株価データ・決算発表は変わらない"""
    prices, earnings = stored_prices(), stored_earnings()

    run_verification(hypothesis, SYMBOLS, PERIOD_START, PERIOD_END, AMOUNT)
    run_verification(hypothesis, SYMBOLS, PERIOD_START, PERIOD_END, AMOUNT)

    assert stored_prices() == prices
    assert stored_earnings() == earnings


def test_verification_uses_only_stored_data(market_data, hypothesis, no_network, fixed_proposals):
    """T037：データが揃っている場合、検証中に yfinance・Alpha Vantage を呼ばない"""
    ticker, urlopen = no_network

    run = run_verification(hypothesis, SYMBOLS, PERIOD_START, PERIOD_END, AMOUNT)

    assert run.status == VerificationRun.STATUS_SUCCESS, run.error_message
    ticker.assert_not_called()
    urlopen.assert_not_called()

