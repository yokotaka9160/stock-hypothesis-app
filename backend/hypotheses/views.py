"""仮説の読み取り・保存・一覧・編集・削除の API（FR-001〜FR-003、FR-017〜FR-024）

保存の流れ：
1. POST /api/hypotheses/parse/ で文章を読み取り、結果を画面に表示する（まだ保存しない）
2. 利用者が確認・書き換え（% と購入方法）をしたら、POST /api/hypotheses/（編集は PUT /api/hypotheses/{id}/）で保存する
文章を編集した場合も、1 からやり直す（FR-022）。
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from advisor.client import GeminiConfigError, GeminiError, GeminiQuotaError, GeminiTimeoutError

from .models import Hypothesis
from .parser import HypothesisParseError, parse_hypothesis
from .serializers import HypothesisSerializer


class HypothesisViewSet(viewsets.ModelViewSet):
    queryset = Hypothesis.objects.all()
    serializer_class = HypothesisSerializer
    http_method_names = ['get', 'post', 'put', 'delete']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer.errors)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object(), data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer.errors)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def parse(self, request):
        """文章を読み取り、結果を返す。保存はしない（FR-017、FR-018）"""
        text = request.data.get('text', '')
        if not isinstance(text, str):
            return _error('仮説の文章を入力してください', status.HTTP_400_BAD_REQUEST)
        try:
            parsed = parse_hypothesis(text)
        except HypothesisParseError as e:
            return _error(
                str(e),
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                missing_items=e.missing_items,
                suggestion=e.suggestion,
            )
        except GeminiQuotaError as e:
            return _error(str(e), status.HTTP_429_TOO_MANY_REQUESTS)
        except GeminiTimeoutError as e:
            return _error(str(e), status.HTTP_504_GATEWAY_TIMEOUT)
        except GeminiConfigError as e:
            return _error(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)
        except GeminiError as e:
            return _error(str(e), status.HTTP_502_BAD_GATEWAY)
        return Response({'text': text.strip(), 'parsed': parsed})


def _error(message: str, status_code: int, **extra) -> Response:
    return Response({'error': message, **extra}, status=status_code)


def _validation_error(errors) -> Response:
    """入力チェックのエラーを、画面に出す1つの文にまとめる"""
    messages = []
    for field_errors in errors.values():
        items = field_errors if isinstance(field_errors, list) else [field_errors]
        messages.extend(str(m) for m in items)
    return _error('。'.join(messages) or '入力内容が正しくありません', status.HTTP_400_BAD_REQUEST)
