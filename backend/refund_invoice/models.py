from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum

from billing.models import RechargeRecord


class RefundRequest(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING, '待审核'),
        (STATUS_APPROVED, '已通过'),
        (STATUS_REJECTED, '已拒绝'),
        (STATUS_CANCELLED, '已撤销'),
    ]

    refund_no = models.CharField(max_length=40, unique=True, verbose_name='退费单号')
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='refund_requests',
        verbose_name='申请人',
    )
    recharge_record = models.ForeignKey(
        RechargeRecord,
        on_delete=models.PROTECT,
        related_name='refund_requests',
        verbose_name='关联充值记录',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='申请退费金额')
    reason = models.CharField(max_length=500, verbose_name='退费原因')
    attachment_url = models.CharField(max_length=500, blank=True, default='', verbose_name='附件链接')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name='状态',
    )
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_refunds',
        verbose_name='审核人',
    )
    review_remark = models.CharField(max_length=500, blank=True, default='', verbose_name='审核备注')
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='审核时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='申请时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'refund_requests'
        ordering = ['-created_at']
        verbose_name = '退费申请'
        verbose_name_plural = '退费申请'

    def __str__(self) -> str:
        return f'{self.refund_no} - {self.user.username} - ¥{self.amount}'

    def clean(self):
        super().clean()
        if self.amount <= 0:
            raise ValidationError({'amount': '退费金额必须大于 0。'})
        if self.recharge_record_id:
            if self.recharge_record.user_id != self.user_id:
                raise ValidationError({'recharge_record': '只能对自己的充值记录申请退费。'})
            total_refunded = (
                RefundRequest.objects.filter(
                    recharge_record=self.recharge_record,
                    status__in=[self.STATUS_PENDING, self.STATUS_APPROVED],
                )
                .exclude(pk=self.pk)
                .aggregate(total=Sum('amount'))
                .get('total') or 0
            )
            remaining = self.recharge_record.amount - total_refunded
            if self.amount > remaining:
                raise ValidationError(
                    {'amount': f'该充值剩余可退金额为 ¥{remaining}，申请金额不得超过该值。'}
                )


class InvoiceTitle(models.Model):
    TYPE_PERSONAL = 'personal'
    TYPE_COMPANY = 'company'

    TYPE_CHOICES = [
        (TYPE_PERSONAL, '个人'),
        (TYPE_COMPANY, '单位'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='invoice_titles',
        verbose_name='所属用户',
    )
    title_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_PERSONAL,
        verbose_name='抬头类型',
    )
    title_name = models.CharField(max_length=200, verbose_name='发票抬头名称')
    tax_no = models.CharField(max_length=50, blank=True, default='', verbose_name='纳税人识别号')
    email = models.EmailField(max_length=200, verbose_name='接收邮箱')
    is_default = models.BooleanField(default=False, verbose_name='是否默认')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'invoice_titles'
        ordering = ['-is_default', '-updated_at']
        verbose_name = '发票抬头'
        verbose_name_plural = '发票抬头'

    def __str__(self) -> str:
        return f'{self.get_title_type_display()} - {self.title_name}'

    def clean(self):
        super().clean()
        if self.title_type == self.TYPE_COMPANY and not self.tax_no:
            raise ValidationError({'tax_no': '单位抬头必须填写纳税人识别号。'})


class InvoiceRequest(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_ISSUED = 'issued'
    STATUS_REJECTED = 'rejected'
    STATUS_VOID = 'void'

    STATUS_CHOICES = [
        (STATUS_PENDING, '待处理'),
        (STATUS_ISSUED, '已开具'),
        (STATUS_REJECTED, '已驳回'),
        (STATUS_VOID, '已作废'),
    ]

    invoice_no = models.CharField(max_length=40, unique=True, verbose_name='开票申请单号')
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='invoice_requests',
        verbose_name='申请人',
    )
    title = models.ForeignKey(
        InvoiceTitle,
        on_delete=models.PROTECT,
        related_name='invoice_requests',
        verbose_name='发票抬头',
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='开票总金额')
    remark = models.CharField(max_length=500, blank=True, default='', verbose_name='备注')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name='状态',
    )
    invoice_number = models.CharField(max_length=100, blank=True, default='', verbose_name='电子发票号')
    download_url = models.CharField(max_length=500, blank=True, default='', verbose_name='发票下载链接')
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_invoices',
        verbose_name='处理人',
    )
    review_remark = models.CharField(max_length=500, blank=True, default='', verbose_name='处理备注')
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='处理时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='申请时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'invoice_requests'
        ordering = ['-created_at']
        verbose_name = '开票申请'
        verbose_name_plural = '开票申请'

    def __str__(self) -> str:
        return f'{self.invoice_no} - ¥{self.total_amount}'


class InvoiceRequestItem(models.Model):
    invoice_request = models.ForeignKey(
        InvoiceRequest,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='开票申请',
    )
    recharge_record = models.ForeignKey(
        RechargeRecord,
        on_delete=models.PROTECT,
        related_name='invoice_items',
        verbose_name='充值记录',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='开票金额')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'invoice_request_items'
        verbose_name = '开票申请明细'
        verbose_name_plural = '开票申请明细'

    def __str__(self) -> str:
        return f'{self.invoice_request.invoice_no} - ¥{self.amount}'
