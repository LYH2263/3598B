import secrets

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Activity(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_ONGOING = 'ongoing'
    STATUS_ENDED = 'ended'

    STATUS_CHOICES = [
        (STATUS_DRAFT, '草稿'),
        (STATUS_PUBLISHED, '已发布'),
        (STATUS_ONGOING, '进行中'),
        (STATUS_ENDED, '已结束'),
    ]

    title = models.CharField(max_length=200, verbose_name='活动标题')
    description = models.TextField(verbose_name='活动介绍')
    cover_image = models.CharField(max_length=500, blank=True, default='', verbose_name='封面图片')
    location = models.CharField(max_length=200, verbose_name='活动地点')
    start_time = models.DateTimeField(verbose_name='开始时间')
    end_time = models.DateTimeField(verbose_name='结束时间')
    max_participants = models.PositiveIntegerField(default=50, verbose_name='人数上限')
    require_approval = models.BooleanField(default=False, verbose_name='是否需要审核报名')
    require_payment = models.BooleanField(default=False, verbose_name='是否需要扣费')
    fee_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='活动费用')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, verbose_name='活动状态')
    check_in_code = models.CharField(max_length=16, blank=True, default='', verbose_name='签到码')
    publisher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='published_activities',
        verbose_name='发布人',
    )
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='发布时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'activities'
        ordering = ['-created_at']
        verbose_name = '校园活动'
        verbose_name_plural = '校园活动'

    def __str__(self) -> str:
        return self.title

    def clean(self):
        super().clean()
        if self.start_time >= self.end_time:
            raise ValidationError({'start_time': '开始时间必须早于结束时间。'})
        if self.max_participants <= 0:
            raise ValidationError({'max_participants': '人数上限必须大于 0。'})
        if self.require_payment and self.fee_amount <= 0:
            raise ValidationError({'fee_amount': '需要扣费时费用必须大于 0。'})

    @property
    def registered_count(self):
        return self.registrations.filter(
            status__in=[ActivityRegistration.STATUS_APPROVED, ActivityRegistration.STATUS_CHECKED_IN]
        ).count()

    @property
    def is_full(self):
        return self.registered_count >= self.max_participants

    @property
    def can_register(self):
        if self.status not in (self.STATUS_PUBLISHED, self.STATUS_ONGOING):
            return False
        if self.end_time < timezone.now():
            return False
        if self.is_full:
            return False
        return True

    def generate_check_in_code(self):
        code = secrets.randbelow(1000000)
        self.check_in_code = f'{code:06d}'
        self.save(update_fields=['check_in_code', 'updated_at'])
        return self.check_in_code


class ActivityRegistration(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHECKED_IN = 'checked_in'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING, '待审核'),
        (STATUS_APPROVED, '已报名'),
        (STATUS_REJECTED, '已驳回'),
        (STATUS_CHECKED_IN, '已签到'),
        (STATUS_CANCELLED, '已取消'),
    ]

    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name='registrations',
        verbose_name='活动',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activity_registrations',
        verbose_name='报名用户',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name='报名状态')
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='已支付金额')
    check_in_time = models.DateTimeField(null=True, blank=True, verbose_name='签到时间')
    review_remark = models.CharField(max_length=255, blank=True, default='', verbose_name='审核备注')
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_activity_registrations',
        verbose_name='审核人',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='审核时间')
    registered_at = models.DateTimeField(auto_now_add=True, verbose_name='报名时间')

    class Meta:
        db_table = 'activity_registrations'
        ordering = ['-registered_at']
        verbose_name = '活动报名'
        verbose_name_plural = '活动报名'
        constraints = [
            models.UniqueConstraint(
                fields=['activity', 'user'],
                name='unique_activity_registration_per_user',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.user.username} - {self.activity.title}'


class ActivityReview(models.Model):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='活动',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activity_reviews',
        verbose_name='评价用户',
    )
    registration = models.OneToOneField(
        ActivityRegistration,
        on_delete=models.CASCADE,
        related_name='review',
        verbose_name='关联报名记录',
    )
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES, verbose_name='评分')
    content = models.TextField(max_length=1000, blank=True, default='', verbose_name='评价内容')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='评价时间')

    class Meta:
        db_table = 'activity_reviews'
        ordering = ['-created_at']
        verbose_name = '活动评价'
        verbose_name_plural = '活动评价'
        constraints = [
            models.UniqueConstraint(
                fields=['activity', 'user'],
                name='unique_activity_review_per_user',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.user.username} 评价 {self.activity.title}: {self.rating}星'
