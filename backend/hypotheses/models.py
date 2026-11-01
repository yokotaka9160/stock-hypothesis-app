from django.db import models


class Hypothesis(models.Model):
    """売買の仮説。text は利用者が入力した文章、parsed はそれを読み取った結果（FR-017、FR-019）"""

    text = models.TextField('仮説の文章')
    # 保存時に一度だけ作成し、検証にはこれを使う（FR-019）。形は parser.validate_parsed を参照
    parsed = models.JSONField('読み取り結果')
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.text[:40]
