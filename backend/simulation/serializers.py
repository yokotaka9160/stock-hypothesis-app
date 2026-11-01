import re
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from hypotheses.models import Hypothesis
from marketdata.services import MAX_HISTORY_DAYS
from marketdata.sessions import EASTERN

from .models import SymbolResult, Trade, VerificationRun

SYMBOL_PATTERN = re.compile(r'^[A-Z0-9][A-Z0-9.\-]{0,15}$')
MAX_SYMBOLS = 20


class VerificationRequestSerializer(serializers.Serializer):
    """検証の条件（FR-004）"""

    hypothesis_id = serializers.PrimaryKeyRelatedField(queryset=Hypothesis.objects.all(), source='hypothesis')
    symbols = serializers.ListField(child=serializers.CharField(), allow_empty=False)
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal('0.01'))

    def validate_symbols(self, value):
        symbols = []
        for raw in value:
            symbol = raw.strip().upper()
            if not SYMBOL_PATTERN.match(symbol):
                raise serializers.ValidationError(f'銘柄「{raw}」が正しくありません（例：AAPL）')
            if symbol not in symbols:
                symbols.append(symbol)
        if len(symbols) > MAX_SYMBOLS:
            raise serializers.ValidationError(f'銘柄は{MAX_SYMBOLS}個までにしてください')
        return symbols

    def validate(self, attrs):
        today = timezone.now().astimezone(EASTERN).date()
        earliest = today - timedelta(days=MAX_HISTORY_DAYS)
        if attrs['period_start'] > attrs['period_end']:
            raise serializers.ValidationError('検証期間の開始日は、終了日より前にしてください')
        if attrs['period_end'] > today:
            raise serializers.ValidationError('検証期間の終了日は、今日以前にしてください')
        if attrs['period_start'] < earliest:
            # yfinance の1時間足は直近730日以内しか取得できない（research 項目1）
            raise serializers.ValidationError(f'検証期間の開始日は {earliest.isoformat()} 以降にしてください（株価データは直近730日分のみ）')
        return attrs


class TradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trade
        fields = ['buy_at', 'buy_price', 'buy_session', 'order_type', 'quantity', 'sell_at', 'sell_price', 'pnl']


class SymbolResultSerializer(serializers.ModelSerializer):
    trades = TradeSerializer(many=True, read_only=True)

    class Meta:
        model = SymbolResult
        fields = ['symbol', 'trade_count', 'pnl', 'unavailable', 'missing_dates', 'trades']


class VerificationRunSerializer(serializers.ModelSerializer):
    symbol_results = SymbolResultSerializer(many=True, read_only=True)
    total_trade_count = serializers.SerializerMethodField()
    total_pnl = serializers.SerializerMethodField()

    class Meta:
        model = VerificationRun
        fields = [
            'id', 'hypothesis', 'hypothesis_text', 'hypothesis_parsed', 'symbols',
            'period_start', 'period_end', 'amount', 'status', 'error_message', 'created_at',
            'total_trade_count', 'total_pnl', 'symbol_results',
        ]

    def _available(self, run):
        return [r for r in run.symbol_results.all() if not r.unavailable]

    def get_total_trade_count(self, run) -> int:
        """全銘柄合計の総取引回数。検証不可の銘柄は含めない（FR-007）"""
        return sum(r.trade_count for r in self._available(run))

    def get_total_pnl(self, run) -> str:
        return str(sum((r.pnl for r in self._available(run)), Decimal('0')))
