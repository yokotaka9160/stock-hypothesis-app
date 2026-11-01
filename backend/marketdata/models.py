from django.db import models

from .sessions import SESSION_CHOICES


class PriceBar(models.Model):
    """株価データ（1時間足）。一度保存したら上書きしない（原則IV）"""

    symbol = models.CharField('銘柄', max_length=16)
    timestamp = models.DateTimeField('足の開始日時')  # UTC で保存し、表示時に米国東部時間に変換する
    open = models.DecimalField('始値', max_digits=18, decimal_places=6)
    high = models.DecimalField('高値', max_digits=18, decimal_places=6)
    low = models.DecimalField('安値', max_digits=18, decimal_places=6)
    close = models.DecimalField('終値', max_digits=18, decimal_places=6)
    volume = models.BigIntegerField('出来高')
    session = models.CharField('時間帯', max_length=8, choices=SESSION_CHOICES)
    fetched_at = models.DateTimeField('取得日時', auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['symbol', 'timestamp'], name='unique_price_bar'),
        ]
        ordering = ['symbol', 'timestamp']

    def __str__(self):
        return f'{self.symbol} {self.timestamp:%Y-%m-%d %H:%M}'


class EarningsEvent(models.Model):
    """決算発表。株価データと同じく、一度保存したら上書きしない（原則IV）"""

    symbol = models.CharField('銘柄', max_length=16)
    announced_at = models.DateTimeField('発表日時')
    # 暦年で数え、1〜3月に発表された決算を第1四半期とする（FR-025）
    fiscal_quarter = models.PositiveSmallIntegerField('四半期')
    fetched_at = models.DateTimeField('取得日時', auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['symbol', 'announced_at'], name='unique_earnings_event'),
        ]
        ordering = ['symbol', 'announced_at']

    def __str__(self):
        return f'{self.symbol} {self.announced_at:%Y-%m-%d %H:%M} Q{self.fiscal_quarter}'
