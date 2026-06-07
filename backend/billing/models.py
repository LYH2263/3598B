from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from dormitory.models import Room


class SavedReport(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_reports')
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=500, blank=True, default='')
    dataset = models.CharField(max_length=50)
    dimensions = models.JSONField(default=list)
    measures = models.JSONField(default=list)
    filters = models.JSONField(default=dict)
    chart_type = models.CharField(max_length=30, default='bar')
    chart_config = models.JSONField(default=dict, blank=True)
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'saved_reports'
        ordering = ['-updated_at']


class DashboardPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='dashboard_pref')
    layout = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dashboard_preferences'


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
    TYPE_REFUND = 'refund'

    CHANGE_TYPE_CHOICES = [
        (TYPE_RECHARGE, '充值入账'),
        (TYPE_CONSUMPTION, '消费扣费'),
        (TYPE_FREEZE, '账户冻结'),
        (TYPE_UNFREEZE, '账户解冻'),
        (TYPE_ADJUST, '余额调整'),
        (TYPE_REFUND, '退费扣减'),
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


class PriceStrategy(models.Model):
    CATEGORY_WATER = ConsumptionRecord.CATEGORY_WATER
    CATEGORY_ELECTRICITY = ConsumptionRecord.CATEGORY_ELECTRICITY
    CATEGORY_CHOICES = ConsumptionRecord.CATEGORY_CHOICES

    TYPE_FLAT = 'flat'
    TYPE_TIERED = 'tiered'

    TYPE_CHOICES = [
        (TYPE_FLAT, '单一单价'),
        (TYPE_TIERED, '分段计价'),
    ]

    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, unique=True, verbose_name='费用类型')
    strategy_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_FLAT, verbose_name='计价方式')
    unit_price = models.DecimalField(max_digits=12, decimal_places=4, default=0, verbose_name='基础单价')
    tiers = models.JSONField(default=list, blank=True, verbose_name='分段配置')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'price_strategies'
        verbose_name = '价格策略'
        verbose_name_plural = '价格策略'

    def __str__(self) -> str:
        return f'{self.get_category_display()} - {self.get_strategy_type_display()}'

    def clean(self):
        super().clean()
        if self.strategy_type == self.TYPE_TIERED:
            if not isinstance(self.tiers, list) or len(self.tiers) == 0:
                raise ValidationError({'tiers': '分段计价必须配置分段数据。'})
            for tier in self.tiers:
                if not all(k in tier for k in ('start', 'end', 'price')):
                    raise ValidationError({'tiers': '每个分段必须包含 start、end、price 字段。'})
        if self.unit_price <= 0:
            raise ValidationError({'unit_price': '基础单价必须大于 0。'})


class MeterReading(models.Model):
    CATEGORY_WATER = ConsumptionRecord.CATEGORY_WATER
    CATEGORY_ELECTRICITY = ConsumptionRecord.CATEGORY_ELECTRICITY
    CATEGORY_CHOICES = ConsumptionRecord.CATEGORY_CHOICES

    SOURCE_ADMIN = 'admin'
    SOURCE_EXTERNAL = 'external'
    SOURCE_AUTO = 'auto'

    SOURCE_CHOICES = [
        (SOURCE_ADMIN, '管理员录入'),
        (SOURCE_EXTERNAL, '外部系统'),
        (SOURCE_AUTO, '自动生成'),
    ]

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='meter_readings',
        verbose_name='房间',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='meter_readings',
        verbose_name='关联学生',
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name='抄表类型')
    period_start = models.DateField(verbose_name='周期开始日期')
    period_end = models.DateField(verbose_name='周期结束日期')
    previous_reading = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='上期表底')
    current_reading = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='本期表底')
    usage = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='本期用量')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default=SOURCE_ADMIN, verbose_name='数据来源')
    operator = models.CharField(max_length=64, blank=True, default='', verbose_name='操作人')
    remark = models.CharField(max_length=255, blank=True, default='', verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'meter_readings'
        ordering = ['-period_end', '-created_at']
        verbose_name = '抄表记录'
        verbose_name_plural = '抄表记录'
        constraints = [
            models.UniqueConstraint(
                fields=['room', 'category', 'period_start', 'period_end'],
                condition=Q(user__isnull=True),
                name='unique_room_meter_reading_per_period',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.room} - {self.get_category_display()} - {self.period_end}'

    def clean(self):
        super().clean()
        if self.current_reading < self.previous_reading:
            raise ValidationError({'current_reading': '本期表底不能小于上期表底。'})
        if self.period_start >= self.period_end:
            raise ValidationError({'period_start': '周期开始日期必须早于结束日期。'})
        if self.usage <= 0 and self.current_reading == self.previous_reading:
            pass
        elif self.usage < 0:
            raise ValidationError({'usage': '用量不能为负数。'})

    def save(self, *args, **kwargs):
        if self.usage == 0:
            self.usage = self.current_reading - self.previous_reading
        super().save(*args, **kwargs)


class UtilityBill(models.Model):
    CATEGORY_WATER = ConsumptionRecord.CATEGORY_WATER
    CATEGORY_ELECTRICITY = ConsumptionRecord.CATEGORY_ELECTRICITY
    CATEGORY_CHOICES = ConsumptionRecord.CATEGORY_CHOICES

    STATUS_PENDING = 'pending'
    STATUS_PAID = 'paid'
    STATUS_VOID = 'void'
    STATUS_MERGED = 'merged'
    STATUS_OVERDUE = 'overdue'

    STATUS_CHOICES = [
        (STATUS_PENDING, '待缴'),
        (STATUS_PAID, '已缴'),
        (STATUS_VOID, '已作废'),
        (STATUS_MERGED, '已合并'),
        (STATUS_OVERDUE, '已逾期'),
    ]

    bill_no = models.CharField(max_length=40, unique=True, verbose_name='账单编号')
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='utility_bills',
        verbose_name='学生用户',
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='utility_bills',
        verbose_name='房间',
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name='费用类型')
    period_start = models.DateField(verbose_name='周期开始日期')
    period_end = models.DateField(verbose_name='周期结束日期')
    previous_reading = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='上期表底')
    current_reading = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='本期表底')
    usage = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='用量')
    price_detail = models.JSONField(default=dict, blank=True, verbose_name='价格明细')
    unit_price = models.DecimalField(max_digits=12, decimal_places=4, default=0, verbose_name='单价')
    base_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='基础金额')
    late_fee_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='滞纳金金额')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='应缴总金额')
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='已缴金额')
    due_date = models.DateField(verbose_name='最后缴费日期')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name='状态')
    meter_reading = models.ForeignKey(
        MeterReading,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bills',
        verbose_name='关联抄表记录',
    )
    parent_bill = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='merged_bills',
        verbose_name='合并至的账单',
    )
    consumption_record = models.ForeignKey(
        ConsumptionRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='utility_bill',
        verbose_name='关联消费记录',
    )
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name='缴费时间')
    operator = models.CharField(max_length=64, blank=True, default='', verbose_name='操作人')
    remark = models.CharField(max_length=255, blank=True, default='', verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'utility_bills'
        ordering = ['-period_end', '-created_at']
        verbose_name = '水电账单'
        verbose_name_plural = '水电账单'

    def __str__(self) -> str:
        return f'{self.bill_no} - {self.user.username} - {self.get_category_display()}'

    @property
    def outstanding_amount(self):
        return self.total_amount - self.paid_amount

    @property
    def is_overdue(self):
        from django.utils import timezone
        return (
            self.status in (self.STATUS_PENDING, self.STATUS_OVERDUE)
            and timezone.now().date() > self.due_date
        )
