from rest_framework import serializers

from .models import Hypothesis
from .parser import HypothesisParseError, validate_parsed


class HypothesisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hypothesis
        fields = ['id', 'text', 'parsed', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_text(self, value):
        if not value.strip():
            raise serializers.ValidationError('仮説の文章を入力してください')
        return value.strip()

    def validate_parsed(self, value):
        try:
            return validate_parsed(value)
        except HypothesisParseError as e:
            raise serializers.ValidationError(str(e)) from e
