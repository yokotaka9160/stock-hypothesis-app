"""Gemini が失敗したときのテスト（T038。FR-010-7、research 項目7）

無料枠の上限（HTTP 429）・60秒応答なし・一時的なエラーが続いた場合に、検証全体が失敗になり、
検証結果・問題点・改善案が1件も保存されないことを確かめる。
Gemini の呼び出しは、advisor.client の一番下（_call）だけを差し替え、再試行などの処理はそのまま通す。
"""
from unittest import mock

import httpx
import pytest
from google.genai import errors

from issues.models import Improvement, Issue
from simulation.models import SymbolResult, Trade, VerificationRun
from simulation.services import run_verification

from .conftest import AMOUNT, PERIOD_END, PERIOD_START, SYMBOLS


def api_error(code: int, status: str) -> errors.APIError:
    return errors.APIError(code, {'error': {'code': code, 'status': status, 'message': 'test'}})


FAILURES = {
    'quota': api_error(429, 'RESOURCE_EXHAUSTED'),
    'timeout': httpx.ReadTimeout('timed out'),
    'unavailable': api_error(503, 'UNAVAILABLE'),
    'connection': httpx.ConnectError('connection refused'),
}


@pytest.fixture
def gemini_configured(settings):
    settings.GEMINI_API_KEY = 'test-key'


@pytest.mark.parametrize('failure', FAILURES.values(), ids=FAILURES.keys())
def test_gemini_failure_fails_whole_verification(market_data, hypothesis, no_network, gemini_configured, failure):
    """T038：Gemini が失敗すると、検証全体が失敗になり、エラー文が記録され、結果は保存されない"""
    with mock.patch('advisor.client._call', side_effect=failure), mock.patch('advisor.client.time.sleep'):
        run = run_verification(hypothesis, SYMBOLS, PERIOD_START, PERIOD_END, AMOUNT)

    run.refresh_from_db()
    assert run.status == VerificationRun.STATUS_FAILED
    assert run.error_message
    assert not SymbolResult.objects.filter(run=run).exists()
    assert not Trade.objects.filter(result__run=run).exists()
    assert not Issue.objects.filter(run=run).exists()
    assert not Improvement.objects.filter(run=run).exists()


def test_no_response_within_60_seconds_fails_whole_verification(market_data, hypothesis, no_network, gemini_configured):
    """T038：一時的なエラーの再試行を含めて60秒を超えたら「応答なし」とし、検証全体を失敗にする"""
    clock = iter(range(0, 1000, 30))  # 呼ぶたびに30秒進む時計
    with mock.patch('advisor.client._call', side_effect=api_error(503, 'UNAVAILABLE')), \
            mock.patch('advisor.client.time.sleep'), \
            mock.patch('advisor.client.time.monotonic', side_effect=lambda: next(clock)):
        run = run_verification(hypothesis, SYMBOLS, PERIOD_START, PERIOD_END, AMOUNT)

    run.refresh_from_db()
    assert run.status == VerificationRun.STATUS_FAILED
    assert '60秒' in run.error_message
    assert not SymbolResult.objects.filter(run=run).exists()


def test_failed_verification_api_returns_error(market_data, hypothesis, no_network, gemini_configured, client):
    """T038：API でも、Gemini の失敗は検証の失敗としてエラー文を返す（T027 の画面表示に使う）"""
    with mock.patch('advisor.client._call', side_effect=FAILURES['quota']):
        response = client.post('/api/verifications/', {
            'hypothesis_id': hypothesis.pk,
            'symbols': SYMBOLS,
            'period_start': PERIOD_START.isoformat(),
            'period_end': PERIOD_END.isoformat(),
            'amount': str(AMOUNT),
        }, content_type='application/json')

    assert response.status_code == 502
    body = response.json()
    assert body['error']
    assert body['run']['status'] == VerificationRun.STATUS_FAILED
    assert body['run']['symbol_results'] == []
