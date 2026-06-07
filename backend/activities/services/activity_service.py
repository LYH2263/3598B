from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from activities.models import Activity, ActivityRegistration, ActivityReview
from billing.models import BalanceChangeLog, Wallet
from notices.services import NotificationService


class ActivityService:
    @staticmethod
    @transaction.atomic
    def register_activity(user, activity: Activity) -> ActivityRegistration:
        if not activity.can_register:
            raise ValidationError('该活动当前不可报名。')

        existing = ActivityRegistration.objects.filter(
            activity=activity,
            user=user,
        ).exclude(status=ActivityRegistration.STATUS_CANCELLED).first()
        if existing:
            raise ValidationError('您已报名该活动。')

        if activity.require_payment and activity.fee_amount > 0:
            wallet, _ = Wallet.objects.select_for_update().get_or_create(user=user)
            if wallet.is_frozen:
                raise ValidationError('账户已冻结，无法完成支付。')
            if wallet.balance < activity.fee_amount:
                raise ValidationError('余额不足，请先充值后再报名。')

            balance_before = wallet.balance
            wallet.balance = balance_before - activity.fee_amount
            wallet.save(update_fields=['balance', 'updated_at'])

            BalanceChangeLog.objects.create(
                user=user,
                wallet=wallet,
                change_type=BalanceChangeLog.TYPE_CONSUMPTION,
                amount_delta=Decimal(-activity.fee_amount),
                balance_before=balance_before,
                balance_after=wallet.balance,
                operator=user.username,
                related_order_no=f'ACT{activity.id}',
                remark=f'活动报名扣费：{activity.title}',
            )
            paid_amount = activity.fee_amount
        else:
            paid_amount = Decimal('0.00')

        if activity.require_approval:
            status = ActivityRegistration.STATUS_PENDING
        else:
            status = ActivityRegistration.STATUS_APPROVED

        registration = ActivityRegistration.objects.create(
            activity=activity,
            user=user,
            status=status,
            paid_amount=paid_amount,
        )

        notify_title = '活动报名成功'
        if status == ActivityRegistration.STATUS_PENDING:
            notify_content = f'您已提交「{activity.title}」的报名申请，请等待管理员审核。'
        else:
            notify_content = f'您已成功报名活动「{activity.title}」，请准时参加。'
        NotificationService.create_user_notification(
            user=user,
            title=notify_title,
            content=notify_content,
            notice_type='system',
        )

        return registration

    @staticmethod
    @transaction.atomic
    def review_registration(
        registration: ActivityRegistration,
        action: str,
        reviewer,
        review_remark: str = '',
    ) -> ActivityRegistration:
        registration = ActivityRegistration.objects.select_for_update().filter(id=registration.id).first()
        if not registration:
            raise ValidationError('报名记录不存在。')
        if registration.status != ActivityRegistration.STATUS_PENDING:
            raise ValidationError('该报名无需审核。')

        if action not in {ActivityRegistration.STATUS_APPROVED, ActivityRegistration.STATUS_REJECTED}:
            raise ValidationError('非法审核动作。')

        if action == ActivityRegistration.STATUS_REJECTED and registration.paid_amount > 0:
            wallet, _ = Wallet.objects.select_for_update().get_or_create(user=registration.user)
            balance_before = wallet.balance
            wallet.balance = balance_before + registration.paid_amount
            wallet.save(update_fields=['balance', 'updated_at'])

            BalanceChangeLog.objects.create(
                user=registration.user,
                wallet=wallet,
                change_type=BalanceChangeLog.TYPE_ADJUST,
                amount_delta=registration.paid_amount,
                balance_before=balance_before,
                balance_after=wallet.balance,
                operator=reviewer.username,
                related_order_no=f'ACT{registration.activity_id}',
                remark=f'活动报名驳回退款：{registration.activity.title}',
            )
            notify_title = '活动报名被驳回'
            notify_content = f'您报名的「{registration.activity.title}」未通过审核。原因：{review_remark or "未填写"}。已支付费用已退回您的账户。'
        else:
            notify_title = '活动报名审核通过'
            notify_content = f'恭喜！您报名的「{registration.activity.title}」已通过审核，请准时参加。'

        registration.status = action
        registration.reviewer = reviewer
        registration.review_remark = review_remark
        registration.reviewed_at = timezone.now()
        registration.save(update_fields=['status', 'reviewer', 'review_remark', 'reviewed_at'])

        NotificationService.create_user_notification(
            user=registration.user,
            title=notify_title,
            content=notify_content,
            notice_type='system',
        )

        return registration

    @staticmethod
    @transaction.atomic
    def batch_review_registrations(
        registration_ids: list,
        action: str,
        reviewer,
        review_remark: str = '',
    ) -> int:
        updated = 0
        for rid in registration_ids:
            try:
                reg = ActivityRegistration.objects.get(id=rid)
                ActivityService.review_registration(reg, action, reviewer, review_remark)
                updated += 1
            except Exception:
                continue
        return updated

    @staticmethod
    @transaction.atomic
    def check_in_by_code(activity: Activity, check_in_code: str, user) -> ActivityRegistration:
        if not activity.check_in_code or activity.check_in_code != check_in_code.strip():
            raise ValidationError('签到码不正确。')
        if activity.status not in (Activity.STATUS_ONGOING, Activity.STATUS_PUBLISHED):
            raise ValidationError('该活动暂不支持签到。')

        registration = ActivityRegistration.objects.filter(
            activity=activity,
            user=user,
            status__in=[ActivityRegistration.STATUS_APPROVED, ActivityRegistration.STATUS_CHECKED_IN],
        ).select_for_update().first()

        if not registration:
            raise ValidationError('您未报名该活动或报名未通过审核。')
        if registration.status == ActivityRegistration.STATUS_CHECKED_IN:
            raise ValidationError('您已完成签到，请勿重复签到。')

        registration.status = ActivityRegistration.STATUS_CHECKED_IN
        registration.check_in_time = timezone.now()
        registration.save(update_fields=['status', 'check_in_time'])

        NotificationService.create_user_notification(
            user=user,
            title='活动签到成功',
            content=f'您已成功签到活动「{activity.title}」。',
            notice_type='system',
        )

        return registration

    @staticmethod
    def update_activity_status():
        now = timezone.now()
        updated_count = 0

        published_to_ongoing = Activity.objects.filter(
            status=Activity.STATUS_PUBLISHED,
            start_time__lte=now,
            end_time__gt=now,
        ).update(status=Activity.STATUS_ONGOING)
        updated_count += published_to_ongoing

        ongoing_to_ended = Activity.objects.filter(
            status__in=[Activity.STATUS_PUBLISHED, Activity.STATUS_ONGOING],
            end_time__lte=now,
        ).update(status=Activity.STATUS_ENDED)
        updated_count += ongoing_to_ended

        return updated_count

    @staticmethod
    def create_review(user, activity: Activity, rating: int, content: str = '') -> ActivityReview:
        if activity.status != Activity.STATUS_ENDED:
            raise ValidationError('活动未结束，暂不可评价。')

        registration = ActivityRegistration.objects.filter(
            activity=activity,
            user=user,
            status=ActivityRegistration.STATUS_CHECKED_IN,
        ).first()
        if not registration:
            raise ValidationError('您未实际参与该活动，不可评价。')

        existing = ActivityReview.objects.filter(activity=activity, user=user).first()
        if existing:
            raise ValidationError('您已评价过该活动。')

        review = ActivityReview.objects.create(
            activity=activity,
            user=user,
            registration=registration,
            rating=rating,
            content=content,
        )
        return review
