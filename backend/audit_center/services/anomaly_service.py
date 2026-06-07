from datetime import timedelta
from decimal import Decimal

from django.db.models import Count
from django.utils import timezone

from audit_center.models import AuditLog


class AnomalyDetectionService:
    LOGIN_FAILURE_THRESHOLD = 5
    LOGIN_FAILURE_WINDOW_MINUTES = 10

    LATE_NIGHT_START_HOUR = 0
    LATE_NIGHT_END_HOUR = 6
    LARGE_RECHARGE_THRESHOLD = Decimal('500.00')

    CROSS_IP_WINDOW_MINUTES = 30
    CROSS_IP_DIFFERENT_COUNT = 2

    @classmethod
    def assess(cls, log: AuditLog) -> None:
        reasons = []

        if cls._check_frequent_login_failures(log):
            reasons.append(f'短时间内登录失败超过 {cls.LOGIN_FAILURE_THRESHOLD} 次')

        if cls._check_late_night_large_recharge(log):
            reasons.append('深夜时段大额充值操作')

        if cls._check_cross_ip_activity(log):
            reasons.append(f'{cls.CROSS_IP_WINDOW_MINUTES} 分钟内出现跨 IP 操作')

        if reasons:
            log.is_suspicious = True
            log.suspicious_reasons = reasons

    @classmethod
    def _check_frequent_login_failures(cls, log: AuditLog) -> bool:
        if log.action != AuditLog.ACTION_LOGIN_FAILED:
            return False

        window_start = timezone.now() - timedelta(minutes=cls.LOGIN_FAILURE_WINDOW_MINUTES)
        target = log.target_display or log.operator_username or ''

        if not target:
            return False

        count = AuditLog.objects.filter(
            action=AuditLog.ACTION_LOGIN_FAILED,
            created_at__gte=window_start,
            target_display=target,
        ).count()

        return count >= cls.LOGIN_FAILURE_THRESHOLD

    @classmethod
    def _check_late_night_large_recharge(cls, log: AuditLog) -> bool:
        if log.category != AuditLog.CATEGORY_ORDER:
            return False

        hour = log.created_at.hour if log.created_at else timezone.now().hour
        is_late_night = cls.LATE_NIGHT_START_HOUR <= hour < cls.LATE_NIGHT_END_HOUR
        if not is_late_night:
            return False

        amount_str = ''
        if log.after_data and isinstance(log.after_data, dict):
            amount_str = str(log.after_data.get('amount', ''))

        try:
            if amount_str:
                amount = Decimal(amount_str)
                return amount >= cls.LARGE_RECHARGE_THRESHOLD
        except Exception:
            pass

        return False

    @classmethod
    def _check_cross_ip_activity(cls, log: AuditLog) -> bool:
        if not log.ip_address or not log.operator_id:
            return False

        window_start = timezone.now() - timedelta(minutes=cls.CROSS_IP_WINDOW_MINUTES)

        recent_ips = AuditLog.objects.filter(
            operator_id=log.operator_id,
            created_at__gte=window_start,
        ).exclude(
            ip_address__isnull=True,
        ).exclude(
            ip_address='',
        ).values_list('ip_address', flat=True).distinct()

        ip_list = list(recent_ips)
        if log.ip_address not in ip_list:
            ip_list.append(log.ip_address)

        return len(set(ip_list)) >= cls.CROSS_IP_DIFFERENT_COUNT

    @classmethod
    def get_suspicious_stats(cls, hours: int = 24) -> dict:
        start_time = timezone.now() - timedelta(hours=hours)

        total_suspicious = AuditLog.objects.filter(
            is_suspicious=True,
            created_at__gte=start_time,
        ).count()

        by_category = dict(
            AuditLog.objects.filter(
                is_suspicious=True,
                created_at__gte=start_time,
            ).values_list('category').annotate(count=Count('id')).order_by()
        )

        by_action = dict(
            AuditLog.objects.filter(
                is_suspicious=True,
                created_at__gte=start_time,
            ).values_list('action').annotate(count=Count('id')).order_by()
        )

        top_users = list(
            AuditLog.objects.filter(
                is_suspicious=True,
                created_at__gte=start_time,
            ).values('operator_id', 'operator_username')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        return {
            'total_suspicious': total_suspicious,
            'by_category': by_category,
            'by_action': by_action,
            'top_users': top_users,
        }
