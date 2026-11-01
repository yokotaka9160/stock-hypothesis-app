from django.db import models

from hypotheses.models import Hypothesis
from marketdata.sessions import SESSION_CHOICES


class VerificationRun(models.Model):
    """検証の実行。仮説を削除すると、検証の実行と、それに属する結果もすべて削除する（FR-003）"""

    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [(STATUS_SUCCESS, '成功'), (STATUS_FAILED, '失敗')]

    hypothesis = models.ForeignKey(Hypothesis, on_delete=models.CASCADE, related_name='runs')
    # 検証した時点の仮説の内容（後で仮説が編集されても、検証結果と食い違わないようにする）
    hypothesis_text = models.TextField('検証した仮説の文章')
    hypothesis_parsed = models.JSONField('検証した仮説の読み取り結果')
    symbols = models.JSONField('銘柄')
    period_start = models.DateField('検証期間の開始日')
    period_end = models.DateField('検証期間の終了日')
    amount = models.DecimalField('購入金額（米ドル）', max_digits=18, decimal_places=2)
    status = models.CharField('状態', max_length=8, choices=STATUS_CHOICES)
    error_message = models.TextField('失敗したときのエラー文', blank=True)
    created_at = models.DateTimeField('実行日時', auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class SymbolResult(models.Model):
    """銘柄ごとの結果。全銘柄の合計は、検証不可でない SymbolResult から計算する（FR-007）"""

    run = models.ForeignKey(VerificationRun, on_delete=models.CASCADE, related_name='symbol_results')
    symbol = models.CharField('銘柄', max_length=16)
    trade_count = models.PositiveIntegerField('取引回数', default=0)
    pnl = models.DecimalField('損益額（米ドル）', max_digits=18, decimal_places=6, default=0)
    unavailable = models.BooleanField('検証不可', default=False)  # FR-009
    # 検証期間の中でデータが欠けていた取引日（FR-009、FR-008b）
    missing_dates = models.JSONField('データが欠けている日', default=list)

    class Meta:
        ordering = ['id']


class Trade(models.Model):
    """取引。約定しなかった回・0株の回・売却する足のデータが欠けている回は記録しない（FR-004a、FR-008、FR-008b）"""

    ORDER_CHOICES = [('stop', '逆指値'), ('limit', '指値')]

    result = models.ForeignKey(SymbolResult, on_delete=models.CASCADE, related_name='trades')
    buy_at = models.DateTimeField('購入日時')  # 約定した1時間足の開始日時
    buy_price = models.DecimalField('購入価格', max_digits=18, decimal_places=6)
    buy_session = models.CharField('購入した時間帯', max_length=8, choices=SESSION_CHOICES)
    order_type = models.CharField('購入方法', max_length=8, choices=ORDER_CHOICES)
    quantity = models.PositiveIntegerField('株数')
    sell_at = models.DateTimeField('売却日時')  # 売却した1時間足の開始日時
    sell_price = models.DecimalField('売却価格', max_digits=18, decimal_places=6)
    pnl = models.DecimalField('損益額（米ドル）', max_digits=18, decimal_places=6)

    class Meta:
        ordering = ['buy_at']
