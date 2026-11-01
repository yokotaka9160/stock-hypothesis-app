"""Gemini を呼び出す共通処理（FR-010-7、FR-018、research 項目5・7）

- 60秒以内に応答がない場合は「応答なし」として GeminiTimeoutError を出す。
- 無料枠の上限に達した場合（HTTP 429）は GeminiQuotaError を出す。再試行はしない。
- Gemini 側の一時的なエラー（HTTP 500・503）だけ、少し待って最大2回まで再試行する。
  再試行を含めて60秒を超えたら「応答なし」とする。
- 最終的に失敗した場合は、呼び出し側で検証全体または保存を失敗として扱う。
"""
import json
import logging
import time

import httpx
from django.conf import settings
from google import genai
from google.genai import errors, types

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 60
# 一時的なエラーのときに再試行するまでの待ち時間（秒）。要素の数が再試行の回数
RETRY_DELAYS = (2, 4)
RETRYABLE_CODES = (500, 503)


class GeminiError(Exception):
    """Gemini の呼び出しに失敗した"""


class GeminiConfigError(GeminiError):
    """APIキーが設定されていない"""


class GeminiTimeoutError(GeminiError):
    """60秒以内に応答がなかった"""


class GeminiQuotaError(GeminiError):
    """無料枠の上限に達した"""


def generate_text(prompt: str) -> str:
    """プロンプトを送り、応答の文章を返す"""
    return _generate(prompt, config=None)


def generate_json(prompt: str, response_schema) -> dict | list:
    """プロンプトを送り、response_schema の形の JSON を返す（構造化出力）"""
    config = types.GenerateContentConfig(
        response_mime_type='application/json',
        response_schema=response_schema,
    )
    text = _generate(prompt, config=config)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise GeminiError('Gemini の応答を読み取れませんでした') from e


def _generate(prompt: str, config) -> str:
    if not settings.GEMINI_API_KEY:
        raise GeminiConfigError('Gemini の APIキーが設定されていません（backend/.env の GEMINI_API_KEY）')

    deadline = time.monotonic() + TIMEOUT_SECONDS
    for attempt in range(len(RETRY_DELAYS) + 1):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            return _call(prompt, config, remaining)
        except errors.APIError as e:
            logger.warning('Gemini の呼び出しに失敗しました（%s %s）: %s', e.code, e.status, e.message)
            if e.code == 429:
                raise GeminiQuotaError('Gemini の無料枠の上限に達しました。時間をおいてやり直してください') from e
            if e.code not in RETRYABLE_CODES:
                raise GeminiError(f'Gemini の呼び出しに失敗しました（{e.code}）') from e
            if attempt == len(RETRY_DELAYS):
                raise GeminiError(
                    f'Gemini が混み合っているため、応答を得られませんでした（{e.code}）。時間をおいてやり直してください'
                ) from e
            delay = RETRY_DELAYS[attempt]
            if time.monotonic() + delay >= deadline:
                break
            time.sleep(delay)
        except httpx.TimeoutException as e:
            raise GeminiTimeoutError(f'Gemini から{TIMEOUT_SECONDS}秒以内に応答がありませんでした') from e
        except httpx.HTTPError as e:
            logger.warning('Gemini に接続できませんでした: %s', e)
            raise GeminiError('Gemini に接続できませんでした') from e
    raise GeminiTimeoutError(f'Gemini から{TIMEOUT_SECONDS}秒以内に応答がありませんでした')


def _call(prompt: str, config, timeout_seconds: float) -> str:
    client = genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options=types.HttpOptions(timeout=max(1, int(timeout_seconds * 1000))),
    )
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=config,
    )
    if not response.text:
        raise GeminiError('Gemini から空の応答が返りました')
    return response.text
