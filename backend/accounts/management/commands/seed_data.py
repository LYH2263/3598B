from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from accounts.models import Profile
from billing.models import RechargeOrder, Wallet
from billing.services.ledger_service import LedgerService
from notices.models import Announcement
from notices.services import NotificationService


class Command(BaseCommand):
    help = '初始化演示数据'

    def handle(self, *args, **options):
        admin_user, _ = User.objects.get_or_create(
            username='admin_3598',
            defaults={'email': 'admin3598@example.com', 'first_name': '系统管理员'},
        )
        admin_user.set_password('Admin@123456')
        admin_user.save()
        admin_profile, _ = Profile.objects.get_or_create(
            user=admin_user,
            defaults={
                'role': Profile.ROLE_ADMIN,
                'phone': '13900003598',
                'security_question': '您最喜欢的颜色是？',
            },
        )
        if not admin_profile.security_answer_hash:
            admin_profile.set_security_answer('蓝色')
            admin_profile.save(update_fields=['security_answer_hash'])
        Wallet.objects.get_or_create(user=admin_user)

        student_user, _ = User.objects.get_or_create(
            username='student_3598',
            defaults={'email': 'student3598@example.com', 'first_name': '演示学生'},
        )
        student_user.set_password('Student@123456')
        student_user.save()
        student_profile, _ = Profile.objects.get_or_create(
            user=student_user,
            defaults={
                'role': Profile.ROLE_STUDENT,
                'student_id': '2023598001',
                'phone': '13800003598',
                'security_question': '您的小学名称是？',
            },
        )
        if not student_profile.security_answer_hash:
            student_profile.set_security_answer('晨光小学')
            student_profile.save(update_fields=['security_answer_hash'])

        Wallet.objects.get_or_create(user=student_user)

        if student_user.recharges.count() == 0 and student_user.consumptions.count() == 0:
            LedgerService.create_recharge(
                user=student_user,
                amount=Decimal('200.00'),
                channel='alipay',
                operator='系统初始化',
                remark='新生入学首充',
            )
            LedgerService.create_consumption(
                user=student_user,
                category='water',
                usage=Decimal('8.50'),
                unit_price=Decimal('1.80'),
                meter_value=Decimal('108.50'),
                operator='系统初始化',
                remark='宿舍冷水费用',
            )
            LedgerService.create_consumption(
                user=student_user,
                category='electricity',
                usage=Decimal('15.20'),
                unit_price=Decimal('0.70'),
                meter_value=Decimal('215.20'),
                operator='系统初始化',
                remark='宿舍照明费用',
            )

        if student_user.recharge_orders.filter(status=RechargeOrder.STATUS_PENDING).count() == 0:
            LedgerService.create_recharge_order(
                user=student_user,
                amount=Decimal('50.00'),
                channel='wechat',
                submit_remark='晚间电费补缴',
            )

        announcement, created = Announcement.objects.get_or_create(
            title='系统上线公告',
            defaults={
                'content': '学生水电充值管理系统已上线，支持充值订单、消费统计和账户通知等功能。',
                'is_active': True,
                'publisher': admin_user,
            },
        )

        if created:
            NotificationService.push_announcement(announcement)

        self.stdout.write(self.style.SUCCESS('演示数据初始化完成。'))
