from django.contrib.auth.models import User
from django.db import models


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_frozen = models.BooleanField(default=False)
    frozen_reason = models.CharField(max_length=255, blank=True)
    frozen_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wallets'


class RechargeOrder(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING, '待审核'),
        (STATUS_APPROVED, '已通过'),
        (STATUS_REJECTED, '已驳回'),
    ]

    CHANNEL_ALIPAY = 'alipay'
    CHANNEL_WECHAT = 'wechat'
    CHANNEL_BANK = 'bank'

    CHANNEL_CHOICES = [
        (CHANNEL_ALIPAY, '支付宝'),
        (CHANNEL_WECHAT, '微信支付'),
        (CHANNEL_BANK, '银行卡'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recharge_orders')
    order_no = models.CharField(max_length=40, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    submit_remark = models.CharField(max_length=255, blank=True)
    review_remark = models.CharField(max_length=255, blank=True)
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_recharge_orders',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'recharge_orders'
        ordering = ['-created_at']


class RechargeRecord(models.Model):
    CHANNEL_ALIPAY = 'alipay'
    CHANNEL_WECHAT = 'wechat'
    CHANNEL_BANK = 'bank'

    CHANNEL_CHOICES = [
        (CHANNEL_ALIPAY, '支付宝'),
        (CHANNEL_WECHAT, '微信支付'),
        (CHANNEL_BANK, '银行卡'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recharges')
    order = models.OneToOneField(
        RechargeOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recharge_record',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    operator = models.CharField(max_length=64)
    remark = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'recharge_records'
        ordering = ['-created_at']


class ConsumptionRecord(models.Model):
    CATEGORY_WATER = 'water'
    CATEGORY_ELECTRICITY = 'electricity'

    CATEGORY_CHOICES = [
        (CATEGORY_WATER, '水费'),
        (CATEGORY_ELECTRICITY, '电费'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='consumptions')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    usage = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    cost_amount = models.DecimalField(max_digits=12, decimal_places=2)
    meter_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    operator = models.CharField(max_length=64)
    remark = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'consumption_records'
        ordering = ['-created_at']


class BalanceChangeLog(models.Model):
    TYPE_RECHARGE = 'recharge'
    TYPE_CONSUMPTION = 'consumption'
    TYPE_FREEZE = 'freeze'
    TYPE_UNFREEZE = 'unfreeze'
    TYPE_ADJUST = 'adjust'

    CHANGE_TYPE_CHOICES = [
        (TYPE_RECHARGE, '充值入账'),
        (TYPE_CONSUMPTION, '消费扣费'),
        (TYPE_FREEZE, '账户冻结'),
        (TYPE_UNFREEZE, '账户解冻'),
        (TYPE_ADJUST, '余额调整'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='balance_logs')
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='change_logs')
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPE_CHOICES)
    amount_delta = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance_before = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    related_order_no = models.CharField(max_length=40, blank=True)
    operator = models.CharField(max_length=64)
    remark = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'balance_change_logs'
        ordering = ['-created_at']
