from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q, UniqueConstraint


class Reminder(models.Model):
    TRIGGER_LOW_BALANCE = 'low_balance'
    TRIGGER_NO_RECHARGE_PREDICTED_OVERDUE = 'no_recharge_predicted_overdue'
    TRIGGER_BILL_DUE_SOON = 'bill_due_soon'
    TRIGGER_BILL_OVERDUE = 'bill_overdue'

    TRIGGER_CHOICES = [
        (TRIGGER_LOW_BALANCE, '余额低于阈值'),
        (TRIGGER_NO_RECHARGE_PREDICTED_OVERDUE, '本月未充值且预计欠费'),
        (TRIGGER_BILL_DUE_SOON, '未缴账单临近到期'),
        (TRIGGER_BILL_OVERDUE, '未缴账单逾期'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_HANDLED = 'handled'
    STATUS_RESOLVED_AUTO = 'resolved_auto'
    STATUS_STOPPED = 'stopped'

    STATUS_CHOICES = [
        (STATUS_PENDING, '待处理'),
        (STATUS_HANDLED, '已处理'),
        (STATUS_RESOLVED_AUTO, '自动解决'),
        (STATUS_STOPPED, '已停止'),
    ]

    CHANNEL_INAPP = 'inapp'
    CHANNEL_EMAIL = 'email'
    CHANNEL_PARENT = 'parent'
    CHANNEL_ADMIN_TICKET = 'admin_ticket'

    CHANNEL_CHOICES = [
        (CHANNEL_INAPP, '站内通知'),
        (CHANNEL_EMAIL, '邮件通知'),
        (CHANNEL_PARENT, '家长通知'),
        (CHANNEL_ADMIN_TICKET, '管理员工单'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reminders',
        verbose_name='学生用户',
    )
    trigger_type = models.CharField(
        max_length=40,
        choices=TRIGGER_CHOICES,
        verbose_name='触发类型',
    )
    trigger_key = models.CharField(
        max_length=128,
        verbose_name='触发幂等键',
        help_text='同一学生同一触发条件的唯一键，用于幂等控制',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name='状态',
    )
    current_channel = models.CharField(
        max_length=30,
        choices=CHANNEL_CHOICES,
        default=CHANNEL_INAPP,
        verbose_name='当前通知渠道',
    )
    escalation_level = models.IntegerField(
        default=0,
        verbose_name='升级层级',
        help_text='0=站内, 1=邮件, 2=家长, 3=管理员工单',
    )
    last_escalated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='上次升级时间',
    )
    title = models.CharField(
        max_length=200,
        verbose_name='提醒标题',
    )
    content = models.TextField(
        verbose_name='提醒内容',
    )
    related_bill_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='关联账单ID',
    )
    threshold_snapshot = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='触发时阈值快照',
    )
    handled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='处理时间',
    )
    handled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='handled_reminders',
        verbose_name='处理人',
    )
    handled_note = models.CharField(
        max_length=500,
        blank=True,
        default='',
        verbose_name='处理备注',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间',
    )

    class Meta:
        db_table = 'reminders'
        ordering = ['-created_at']
        verbose_name = '催缴提醒'
        verbose_name_plural = '催缴提醒'
        constraints = [
            UniqueConstraint(
                fields=['user', 'trigger_key'],
                condition=Q(status__in=['pending', 'stopped']),
                name='unique_active_reminder_per_trigger',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.user.username} - {self.get_trigger_type_display()} - {self.get_status_display()}'

    @property
    def is_active(self) -> bool:
        return self.status == self.STATUS_PENDING


class ReminderEvent(models.Model):
    reminder = models.ForeignKey(
        Reminder,
        on_delete=models.CASCADE,
        related_name='events',
        verbose_name='关联提醒',
    )
    channel = models.CharField(
        max_length=30,
        choices=Reminder.CHANNEL_CHOICES,
        verbose_name='通知渠道',
    )
    sent_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='发送时间',
    )
    is_successful = models.BooleanField(
        default=True,
        verbose_name='是否成功',
    )
    error_message = models.CharField(
        max_length=500,
        blank=True,
        default='',
        verbose_name='错误信息',
    )
    notification_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='关联站内通知ID',
    )
    extra_info = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='扩展信息',
    )

    class Meta:
        db_table = 'reminder_events'
        ordering = ['-sent_at']
        verbose_name = '提醒发送事件'
        verbose_name_plural = '提醒发送事件'

    def __str__(self) -> str:
        return f'{self.reminder.id} - {self.get_channel_display()}'


class StudentReminderExemption(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='reminder_exemption',
        verbose_name='学生用户',
    )
    is_exempted = models.BooleanField(
        default=False,
        verbose_name='是否免除所有催缴',
    )
    exempted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exempted_students',
        verbose_name='设置人',
    )
    exempted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='设置时间',
    )
    reason = models.CharField(
        max_length=500,
        blank=True,
        default='',
        verbose_name='免除原因',
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='到期时间（空为永久）',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间',
    )

    class Meta:
        db_table = 'student_reminder_exemptions'
        verbose_name = '学生催缴免除'
        verbose_name_plural = '学生催缴免除'

    def __str__(self) -> str:
        status = '已免除' if self.is_exempted else '正常'
        return f'{self.user.username} - {status}'
