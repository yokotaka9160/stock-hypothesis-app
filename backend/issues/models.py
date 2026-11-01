from django.db import models

from simulation.models import VerificationRun


class Issue(models.Model):
    """仮説の問題点（FR-010-1〜FR-010-4）。1件もなければ「問題は未発見」と表示する（FR-010-6）"""

    ASPECT_TIME_OF_DAY = 'time_of_day'
    ASPECT_TRIGGER = 'trigger'
    ASPECT_TRIGGER_VALUE = 'trigger_value'
    ASPECT_TRADE_COUNT = 'trade_count'
    ASPECT_CHOICES = [
        (ASPECT_TIME_OF_DAY, '時間帯'),
        (ASPECT_TRIGGER, 'トリガー条件'),
        (ASPECT_TRIGGER_VALUE, 'トリガー条件の数値'),
        (ASPECT_TRADE_COUNT, '取引回数'),
    ]

    run = models.ForeignKey(VerificationRun, on_delete=models.CASCADE, related_name='issues')
    aspect = models.CharField('観点', max_length=16, choices=ASPECT_CHOICES)
    reason = models.TextField('理由')
    position = models.PositiveSmallIntegerField('表示の順序')

    class Meta:
        ordering = ['position']


class Improvement(models.Model):
    """改善案。問題点の有無にかかわらず出す（FR-010-5、FR-010-7）"""

    KIND_NUMERIC = 'numeric'
    KIND_AI = 'ai'
    KIND_CHOICES = [(KIND_NUMERIC, '数値'), (KIND_AI, '時間帯・トリガー')]

    run = models.ForeignKey(VerificationRun, on_delete=models.CASCADE, related_name='improvements')
    # 対象の問題点。問題点がない場合は空
    issue = models.ForeignKey(Issue, on_delete=models.SET_NULL, null=True, blank=True, related_name='improvements')
    kind = models.CharField('種類', max_length=8, choices=KIND_CHOICES)
    # 数値の場合は % と購入方法の説明、AI の場合は提案の文章
    proposal = models.TextField('提案内容')
    # 数値の改善案の % と購入方法。AI の提案では空
    buy_percent = models.DecimalField('購入条件の %', max_digits=6, decimal_places=2, null=True, blank=True)
    order_type = models.CharField('購入方法', max_length=8, blank=True)
    # 再検証の結果。AI の提案は再検証しないので空（FR-010-7）
    result_pnl = models.DecimalField('再検証の損益額', max_digits=18, decimal_places=6, null=True, blank=True)
    result_trade_count = models.IntegerField('再検証の総取引回数', null=True, blank=True)
    note = models.TextField('注意書き')
    position = models.PositiveSmallIntegerField('表示の順序')

    class Meta:
        ordering = ['position']
