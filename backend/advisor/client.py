"""Gemini を呼び出す共通処理（FR-010-7、FR-018、research 項目5・7）

- 60秒以内に応答がない場合は「応答なし」として GeminiTimeoutError を出す。
- 無料枠の上限に達した場合（HTTP 429）は GeminiQuotaError を出す。
- 失敗しても再試行はしない。呼び出し側で、検証全体または保存を失敗として扱う。
"""
import json

import httpx
from django.conf import settings
from google import genai
from google.genai import errors, types

TIMEOUT_SECONDS = 60


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

    client = genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options=types.HttpOptions(timeout=TIMEOUT_SECONDS * 1000),
    )
    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=config,
        )
    except errors.APIError as e:
        if e.code == 429:
            raise GeminiQuotaError('Gemini の無料枠の上限に達しました。時間をおいてやり直してください') from e
        raise GeminiError(f'Gemini の呼び出しに失敗しました（{e.code}）') from e
    except httpx.TimeoutException as e:
        raise GeminiTimeoutError(f'Gemini から{TIMEOUT_SECONDS}秒以内に応答がありませんでした') from e
    except httpx.HTTPError as e:
        raise GeminiError('Gemini に接続できませんでした') from e

    if not response.text:
        raise GeminiError('Gemini から空の応答が返りました')
    return response.text
