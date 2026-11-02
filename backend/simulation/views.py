"""検証の API（FR-004〜FR-011）

POST /api/verifications/ で検証を実行し、結果を返す（最大10分。FR-015）。
GET /api/verifications/?hypothesis={id} で、その仮説の検証結果を新しい順に返す。
"""
from rest_framework import mixins, status, viewsets
from rest_framework.response import Response

from .models import VerificationRun
from .serializers import VerificationRequestSerializer, VerificationRunSerializer
from .services import run_verification


class VerificationRunViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = VerificationRunSerializer

    def get_queryset(self):
        queryset = VerificationRun.objects.prefetch_related('symbol_results__trades', 'issues', 'improvements')
        hypothesis_id = self.request.query_params.get('hypothesis')
        if hypothesis_id:
            queryset = queryset.filter(hypothesis_id=hypothesis_id)
        return queryset

    def create(self, request):
        request_serializer = VerificationRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            return Response({'error': _first_error(request_serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)
        data = request_serializer.validated_data
        run = run_verification(
            data['hypothesis'], data['symbols'], data['period_start'], data['period_end'], data['amount']
        )
        body = VerificationRunSerializer(self.get_queryset().get(pk=run.pk)).data
        if run.status == VerificationRun.STATUS_FAILED:
            # 検証が失敗した場合も、エラー文を含めて記録を返す（T027）
            return Response({'error': run.error_message, 'run': body}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(body, status=status.HTTP_201_CREATED)


def _first_error(errors) -> str:
    """入力チェックのエラーを、画面に出す1つの文にまとめる"""
    messages = []
    for value in errors.values():
        items = value if isinstance(value, list) else [value]
        for item in items:
            if isinstance(item, dict):
                messages.append(_first_error(item))
            else:
                messages.append(str(item))
    return '。'.join(messages) or '入力内容が正しくありません'
