from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Profile
from billing.models import BalanceChangeLog, RechargeOrder, Wallet
from billing.services.ledger_service import LedgerService


class BillingFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.admin = User.objects.create_user(username='admin_user', password='Admin@123456', email='admin@test.com')
        Profile.objects.create(user=self.admin, role=Profile.ROLE_ADMIN, phone='13900000001')
        Wallet.objects.create(user=self.admin)

        self.student = User.objects.create_user(username='student_user', password='Student@123456', email='stu@test.com')
        student_profile = Profile.objects.create(
            user=self.student,
            role=Profile.ROLE_STUDENT,
            student_id='20260002',
            phone='13800000002',
            security_question='测试问题',
        )
        student_profile.set_security_answer('答案')
        student_profile.save(update_fields=['security_answer_hash'])
        Wallet.objects.create(user=self.student, balance=Decimal('100.00'))

    def test_student_order_admin_approve_updates_balance_and_log(self):
        student_client = APIClient()
        student_client.force_authenticate(self.student)

        create_response = student_client.post(
            '/api/billing/recharge-orders/',
            {'amount': '50.00', 'channel': 'wechat', 'submit_remark': '测试充值'},
            format='json',
        )
        self.assertEqual(create_response.status_code, 201)
        order_id = create_response.json()['id']

        admin_client = APIClient()
        admin_client.force_authenticate(self.admin)
        review_response = admin_client.post(
            f'/api/billing/recharge-orders/{order_id}/review/',
            {'action': 'approved', 'review_remark': '通过'},
            format='json',
        )
        self.assertEqual(review_response.status_code, 200)

        self.student.wallet.refresh_from_db()
        self.assertEqual(self.student.wallet.balance, Decimal('150.00'))

        self.assertTrue(
            BalanceChangeLog.objects.filter(
                user=self.student,
                change_type=BalanceChangeLog.TYPE_RECHARGE,
            ).exists()
        )

    def test_frozen_wallet_blocks_order_submission(self):
        LedgerService.freeze_wallet(self.student, operator='admin_user', reason='测试冻结')

        student_client = APIClient()
        student_client.force_authenticate(self.student)

        response = student_client.post(
            '/api/billing/recharge-orders/',
            {'amount': '20.00', 'channel': 'alipay'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('账户已冻结', str(response.json()))


class AnnouncementPushTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(username='notice_admin', password='Admin@123456', email='nadmin@test.com')
        Profile.objects.create(user=self.admin, role=Profile.ROLE_ADMIN, phone='13900000003')

        self.student = User.objects.create_user(username='notice_student', password='Student@123456', email='nstudent@test.com')
        Profile.objects.create(user=self.student, role=Profile.ROLE_STUDENT, student_id='20260003', phone='13800000003')

    def test_publish_announcement_pushes_notifications(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            '/api/notices/announcements/',
            {'title': '测试公告', 'content': '公告内容', 'is_active': True},
            format='json',
        )
        self.assertEqual(response.status_code, 201)

        self.client.force_authenticate(self.student)
        notice_response = self.client.get('/api/notices/notifications/')
        self.assertEqual(notice_response.status_code, 200)
        self.assertGreaterEqual(notice_response.json()['unread_count'], 1)
