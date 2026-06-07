import logging
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from billing.models import RechargeRecord, UtilityBill, Wallet
from config_center.services import ConfigService
from notices.models import UserNotification
from notices.services import NotificationService
from reminder.models import Reminder, ReminderEvent, StudentReminderExemption

logger = logging.getLogger(__name__)

ESCALATION_CHANNELS = [
    Reminder.CHANNEL_INAPP,
    Reminder.CHANNEL_EMAIL,
    Reminder.CHANNEL_PARENT,
    Reminder.CHANNEL_ADMIN_TICKET,
]


class ReminderService:
    @staticmethod
    def _is_user_exempted(user) -> bool:
        exemption = getattr(user, 'reminder_exemption', None)
        if not exemption or not exemption.is_exempted:
            return False
        if exemption.expires_at and exemption.expires_at < timezone.now():
            return False
        return True

    @staticmethod
    def _get_threshold_config(user) -> dict:
        campus = None
        profile = getattr(user, 'profile', None)
        if profile and profile.campus:
            campus = profile.campus

        get = lambda g, k, d: ConfigService.get_decimal(g, k, campus) or Decimal(str(d))
        get_int = lambda g, k, d: ConfigService.get_int(g, k, campus) or d

        return {
            'low_balance_threshold': get('wallet', 'auto_recharge_threshold', 20),
            'bill_due_soon_days': get_int('reminder', 'bill_due_soon_days', 3),
            'escalation_interval_days': get_int('reminder', 'escalation_interval_days', 3),
            'no_recharge_days_threshold': get_int('reminder', 'no_recharge_days_threshold', 30),
            'predicted_consumption_daily': get('reminder', 'predicted_consumption_daily', 5),
        }

    @staticmethod
    def _build_trigger_key(trigger_type: str, user_id: int, extra: str = '') -> str:
        if extra:
            return f'{trigger_type}:{user_id}:{extra}'
        return f'{trigger_type}:{user_id}'

    @staticmethod
    def _reminder_exists(user, trigger_key: str) -> bool:
        return Reminder.objects.filter(
            user=user,
            trigger_key=trigger_key,
            status__in=[Reminder.STATUS_PENDING, Reminder.STATUS_STOPPED],
        ).exists()

    @staticmethod
    def _send_channel_notification(reminder: Reminder, channel: str) -> ReminderEvent:
        event = ReminderEvent(reminder=reminder, channel=channel, is_successful=True)

        try:
            if channel == Reminder.CHANNEL_INAPP:
                notification = NotificationService.create_user_notification(
                    user=reminder.user,
                    title=f'【催缴提醒】{reminder.title}',
                    content=reminder.content,
                    notice_type=UserNotification.TYPE_BILLING,
                )
                event.notification_id = notification.id

            elif channel == Reminder.CHANNEL_EMAIL:
                logger.info(
                    '[催缴-邮件] 向 %s(%s) 发送邮件提醒: %s',
                    reminder.user.username,
                    getattr(reminder.user, 'email', ''),
                    reminder.title,
                )

            elif channel == Reminder.CHANNEL_PARENT:
                logger.info(
                    '[催缴-家长] 向 %s 的家长发送通知: %s',
                    reminder.user.username,
                    reminder.title,
                )

            elif channel == Reminder.CHANNEL_ADMIN_TICKET:
                logger.info(
                    '[催缴-管理员工单] 为学生 %s 创建管理员介入工单: %s',
                    reminder.user.username,
                    reminder.title,
                )

        except Exception as e:
            event.is_successful = False
            event.error_message = str(e)
            logger.exception('发送催缴通知失败: reminder_id=%s channel=%s', reminder.id, channel)

        event.save()
        return event

    @staticmethod
    def create_reminder(
        user,
        trigger_type: str,
        trigger_key: str,
        title: str,
        content: str,
        related_bill_id: int | None = None,
        threshold_snapshot: dict | None = None,
    ) -> Reminder | None:
        if ReminderService._is_user_exempted(user):
            return None
        if ReminderService._reminder_exists(user, trigger_key):
            return None

        with transaction.atomic():
            reminder = Reminder.objects.create(
                user=user,
                trigger_type=trigger_type,
                trigger_key=trigger_key,
                title=title,
                content=content,
                related_bill_id=related_bill_id,
                threshold_snapshot=threshold_snapshot or {},
                current_channel=Reminder.CHANNEL_INAPP,
                escalation_level=0,
                last_escalated_at=timezone.now(),
            )
            ReminderService._send_channel_notification(reminder, Reminder.CHANNEL_INAPP)

        logger.info('创建催缴提醒: user=%s trigger=%s id=%s', user.username, trigger_type, reminder.id)
        return reminder

    @staticmethod
    def check_low_balance(user) -> Reminder | None:
        wallet = getattr(user, 'wallet', None)
        if not wallet:
            return None

        thresholds = ReminderService._get_threshold_config(user)
        threshold = thresholds['low_balance_threshold']

        if wallet.balance >= threshold:
            return None

        trigger_key = ReminderService._build_trigger_key(
            Reminder.TRIGGER_LOW_BALANCE,
            user.id,
            f'threshold_{threshold}',
        )

        title = '账户余额不足提醒'
        content = (
            f'您的账户当前余额为 ¥{wallet.balance}，已低于提醒阈值 ¥{threshold}。'
            f'请及时充值以避免影响正常使用。'
        )

        return ReminderService.create_reminder(
            user=user,
            trigger_type=Reminder.TRIGGER_LOW_BALANCE,
            trigger_key=trigger_key,
            title=title,
            content=content,
            threshold_snapshot={
                'balance': str(wallet.balance),
                'threshold': str(threshold),
            },
        )

    @staticmethod
    def check_no_recharge_predicted_overdue(user) -> Reminder | None:
        wallet = getattr(user, 'wallet', None)
        if not wallet:
            return None

        thresholds = ReminderService._get_threshold_config(user)
        no_recharge_days = thresholds['no_recharge_days_threshold']
        daily_cost = thresholds['predicted_consumption_daily']

        cutoff_date = date.today() - timedelta(days=no_recharge_days)
        has_recharged = RechargeRecord.objects.filter(
            user=user,
            created_at__date__gte=cutoff_date,
        ).exists()

        if has_recharged:
            return None

        predicted_days = 0
        if daily_cost > 0 and wallet.balance > 0:
            predicted_days = int(wallet.balance / daily_cost)

        if predicted_days > 7:
            return None

        month_str = date.today().strftime('%Y-%m')
        trigger_key = ReminderService._build_trigger_key(
            Reminder.TRIGGER_NO_RECHARGE_PREDICTED_OVERDUE,
            user.id,
            month_str,
        )

        title = '久未充值提醒'
        if predicted_days <= 0:
            content = (
                f'您已超过 {no_recharge_days} 天未充值，当前余额 ¥{wallet.balance} 预计已不足以支付费用。'
                f'请尽快充值。'
            )
        else:
            content = (
                f'您已超过 {no_recharge_days} 天未充值，当前余额 ¥{wallet.balance} '
                f'预计仅可使用约 {predicted_days} 天。请及时充值。'
            )

        return ReminderService.create_reminder(
            user=user,
            trigger_type=Reminder.TRIGGER_NO_RECHARGE_PREDICTED_OVERDUE,
            trigger_key=trigger_key,
            title=title,
            content=content,
            threshold_snapshot={
                'balance': str(wallet.balance),
                'no_recharge_days': no_recharge_days,
                'predicted_days': predicted_days,
            },
        )

    @staticmethod
    def check_bill_due_soon(user) -> list[Reminder]:
        thresholds = ReminderService._get_threshold_config(user)
        due_soon_days = thresholds['bill_due_soon_days']

        today = date.today()
        cutoff = today + timedelta(days=due_soon_days)

        pending_bills = UtilityBill.objects.filter(
            user=user,
            status__in=[UtilityBill.STATUS_PENDING, UtilityBill.STATUS_OVERDUE],
            due_date__gte=today,
            due_date__lte=cutoff,
        )

        created = []
        for bill in pending_bills:
            trigger_key = ReminderService._build_trigger_key(
                Reminder.TRIGGER_BILL_DUE_SOON,
                user.id,
                f'bill_{bill.id}',
            )

            days_left = (bill.due_date - today).days
            title = f'{bill.get_category_display()}账单即将到期'
            content = (
                f'您的{bill.get_category_display()}账单（{bill.bill_no}）'
                f'应缴金额 ¥{bill.outstanding_amount}，将于 {bill.due_date} 到期，'
                f'距今日还有 {days_left} 天。请及时缴费。'
            )

            reminder = ReminderService.create_reminder(
                user=user,
                trigger_type=Reminder.TRIGGER_BILL_DUE_SOON,
                trigger_key=trigger_key,
                title=title,
                content=content,
                related_bill_id=bill.id,
                threshold_snapshot={
                    'bill_no': bill.bill_no,
                    'outstanding_amount': str(bill.outstanding_amount),
                    'due_date': str(bill.due_date),
                    'days_left': days_left,
                },
            )
            if reminder:
                created.append(reminder)

        return created

    @staticmethod
    def check_bill_overdue(user) -> list[Reminder]:
        today = date.today()

        overdue_bills = UtilityBill.objects.filter(
            user=user,
            status__in=[UtilityBill.STATUS_PENDING, UtilityBill.STATUS_OVERDUE],
            due_date__lt=today,
        )

        created = []
        for bill in overdue_bills:
            trigger_key = ReminderService._build_trigger_key(
                Reminder.TRIGGER_BILL_OVERDUE,
                user.id,
                f'bill_{bill.id}',
            )

            overdue_days = (today - bill.due_date).days
            title = f'{bill.get_category_display()}账单已逾期'
            content = (
                f'您的{bill.get_category_display()}账单（{bill.bill_no}）'
                f'应缴金额 ¥{bill.outstanding_amount}，已于 {bill.due_date} 到期，'
                f'已逾期 {overdue_days} 天。请立即缴费，避免产生更多滞纳金。'
            )

            reminder = ReminderService.create_reminder(
                user=user,
                trigger_type=Reminder.TRIGGER_BILL_OVERDUE,
                trigger_key=trigger_key,
                title=title,
                content=content,
                related_bill_id=bill.id,
                threshold_snapshot={
                    'bill_no': bill.bill_no,
                    'outstanding_amount': str(bill.outstanding_amount),
                    'due_date': str(bill.due_date),
                    'overdue_days': overdue_days,
                },
            )
            if reminder:
                created.append(reminder)

            if bill.status == UtilityBill.STATUS_PENDING:
                bill.status = UtilityBill.STATUS_OVERDUE
                bill.save(update_fields=['status', 'updated_at'])

        return created

    @staticmethod
    def scan_user(user) -> dict:
        if ReminderService._is_user_exempted(user):
            return {'user': user.username, 'exempted': True, 'created': 0}

        created_count = 0
        r = ReminderService.check_low_balance(user)
        if r:
            created_count += 1
        r = ReminderService.check_no_recharge_predicted_overdue(user)
        if r:
            created_count += 1
        created_count += len(ReminderService.check_bill_due_soon(user))
        created_count += len(ReminderService.check_bill_overdue(user))

        return {'user': user.username, 'exempted': False, 'created': created_count}

    @staticmethod
    def scan_all_students() -> dict:
        from accounts.models import Profile

        student_users = User.objects.filter(
            profile__role=Profile.ROLE_STUDENT,
            is_active=True,
        ).select_related('profile', 'wallet')

        total = student_users.count()
        created_total = 0
        exempted_total = 0

        for user in student_users.iterator(chunk_size=200):
            result = ReminderService.scan_user(user)
            if result['exempted']:
                exempted_total += 1
            created_total += result['created']

        logger.info(
            '催缴扫描完成: 扫描学生 %d 人, 免除 %d 人, 新建提醒 %d 条',
            total,
            exempted_total,
            created_total,
        )
        return {
            'scanned': total,
            'exempted': exempted_total,
            'created': created_total,
        }

    @staticmethod
    def escalate_reminders() -> dict:
        thresholds = ReminderService._get_threshold_config(None)
        interval_days = thresholds['escalation_interval_days']
        if interval_days <= 0:
            interval_days = 3

        now = timezone.now()
        cutoff = now - timedelta(days=interval_days)

        pending_reminders = Reminder.objects.filter(
            status=Reminder.STATUS_PENDING,
        ).select_related('user')

        escalated = 0
        already_max = 0

        for reminder in pending_reminders.iterator(chunk_size=200):
            if ReminderService._is_user_exempted(reminder.user):
                continue

            last_escalated = reminder.last_escalated_at or reminder.created_at
            if last_escalated > cutoff:
                continue

            next_level = reminder.escalation_level + 1
            if next_level >= len(ESCALATION_CHANNELS):
                already_max += 1
                continue

            next_channel = ESCALATION_CHANNELS[next_level]

            with transaction.atomic():
                reminder.escalation_level = next_level
                reminder.current_channel = next_channel
                reminder.last_escalated_at = now
                reminder.save(update_fields=[
                    'escalation_level',
                    'current_channel',
                    'last_escalated_at',
                    'updated_at',
                ])
                ReminderService._send_channel_notification(reminder, next_channel)

            escalated += 1
            logger.info(
                '催缴升级: reminder_id=%s user=%s 升级到 %s',
                reminder.id,
                reminder.user.username,
                next_channel,
            )

        logger.info(
            '催缴升级扫描完成: 升级 %d 条, 已达最高级 %d 条',
            escalated,
            already_max,
        )
        return {
            'escalated': escalated,
            'already_max': already_max,
        }

    @staticmethod
    def auto_resolve_reminders() -> dict:
        now = timezone.now()
        today = now.date()
        resolved_count = 0

        pending_reminders = Reminder.objects.filter(
            status=Reminder.STATUS_PENDING,
        ).select_related('user', 'user__wallet')

        for reminder in pending_reminders.iterator(chunk_size=200):
            resolved = False

            if reminder.trigger_type == Reminder.TRIGGER_LOW_BALANCE:
                wallet = getattr(reminder.user, 'wallet', None)
                thresholds = ReminderService._get_threshold_config(reminder.user)
                if wallet and wallet.balance >= thresholds['low_balance_threshold']:
                    resolved = True

            elif reminder.trigger_type == Reminder.TRIGGER_NO_RECHARGE_PREDICTED_OVERDUE:
                cutoff_dt = max(datetime.combine(today - timedelta(days=90), datetime.min.time(), tzinfo=now.tzinfo), reminder.created_at)
                has_recharged = RechargeRecord.objects.filter(
                    user=reminder.user,
                    created_at__gte=cutoff_dt,
                ).exists()
                if has_recharged:
                    resolved = True

            elif reminder.trigger_type in (Reminder.TRIGGER_BILL_DUE_SOON, Reminder.TRIGGER_BILL_OVERDUE):
                if reminder.related_bill_id:
                    bill = UtilityBill.objects.filter(id=reminder.related_bill_id).first()
                    if bill and bill.status in (UtilityBill.STATUS_PAID, UtilityBill.STATUS_VOID):
                        resolved = True

            if resolved:
                reminder.status = Reminder.STATUS_RESOLVED_AUTO
                reminder.handled_at = now
                reminder.save(update_fields=['status', 'handled_at', 'updated_at'])
                resolved_count += 1
                logger.info(
                    '催缴自动解决: reminder_id=%s user=%s trigger=%s',
                    reminder.id,
                    reminder.user.username,
                    reminder.trigger_type,
                )

        logger.info('催缴自动解决完成: %d 条', resolved_count)
        return {'resolved': resolved_count}

    @staticmethod
    def mark_handled(reminder: Reminder, handled_by=None, note: str = '') -> Reminder:
        if reminder.status != Reminder.STATUS_PENDING:
            return reminder

        reminder.status = Reminder.STATUS_HANDLED
        reminder.handled_at = timezone.now()
        reminder.handled_by = handled_by
        reminder.handled_note = note
        reminder.save(update_fields=['status', 'handled_at', 'handled_by', 'handled_note', 'updated_at'])
        return reminder

    @staticmethod
    def stop_reminder(reminder: Reminder, stopped_by=None, note: str = '') -> Reminder:
        if reminder.status != Reminder.STATUS_PENDING:
            return reminder

        reminder.status = Reminder.STATUS_STOPPED
        reminder.handled_at = timezone.now()
        reminder.handled_by = stopped_by
        reminder.handled_note = note
        reminder.save(update_fields=['status', 'handled_at', 'handled_by', 'handled_note', 'updated_at'])
        return reminder

    @staticmethod
    def stop_all_for_user(user, stopped_by=None, reason: str = '') -> StudentReminderExemption:
        exemption, _ = StudentReminderExemption.objects.get_or_create(user=user)
        exemption.is_exempted = True
        exemption.exempted_by = stopped_by
        exemption.exempted_at = timezone.now()
        exemption.reason = reason
        exemption.expires_at = None
        exemption.save()

        stopped_count = Reminder.objects.filter(
            user=user,
            status=Reminder.STATUS_PENDING,
        ).update(
            status=Reminder.STATUS_STOPPED,
            handled_at=timezone.now(),
            handled_by=stopped_by,
            handled_note=f'管理员停止所有催缴: {reason}' if reason else '管理员停止所有催缴',
        )
        logger.info(
            '停止学生所有催缴: user=%s stopped_count=%d reason=%s',
            user.username,
            stopped_count,
            reason,
        )
        return exemption

    @staticmethod
    def resume_for_user(user, resumed_by=None) -> StudentReminderExemption:
        exemption, _ = StudentReminderExemption.objects.get_or_create(user=user)
        exemption.is_exempted = False
        exemption.exempted_by = None
        exemption.exempted_at = None
        exemption.reason = ''
        exemption.save()
        logger.info('恢复学生催缴: user=%s', user.username)
        return exemption

    @staticmethod
    def trigger_manual_reminder(
        user,
        trigger_type: str,
        title: str,
        content: str,
        triggered_by=None,
        related_bill_id: int | None = None,
    ) -> Reminder:
        trigger_key = ReminderService._build_trigger_key(
            trigger_type,
            user.id,
            f'manual_{int(timezone.now().timestamp())}',
        )

        reminder = Reminder.objects.create(
            user=user,
            trigger_type=trigger_type,
            trigger_key=trigger_key,
            title=title,
            content=content,
            related_bill_id=related_bill_id,
            threshold_snapshot={'manual': True, 'triggered_by': getattr(triggered_by, 'username', '')},
            current_channel=Reminder.CHANNEL_INAPP,
            escalation_level=0,
            last_escalated_at=timezone.now(),
        )
        ReminderService._send_channel_notification(reminder, Reminder.CHANNEL_INAPP)
        logger.info(
            '手动触发催缴: user=%s trigger=%s by=%s',
            user.username,
            trigger_type,
            getattr(triggered_by, 'username', ''),
        )
        return reminder
