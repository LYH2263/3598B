import re

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Profile


class PasswordResetFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='reset_user',
            email='reset_user@example.com',
            password='OldPass@123',
        )
        profile = Profile.objects.create(
            user=self.user,
            role=Profile.ROLE_STUDENT,
            student_id='20260001',
            phone='13800138000',
            security_question='测试问题',
        )
        profile.set_security_answer('测试答案')
        profile.save(update_fields=['security_answer_hash'])

    def _captcha_payload(self):
        response = self.client.get('/api/auth/captcha/')
        data = response.json()
        match = re.search(r'(\d+)\s*([+-])\s*(\d+)', data['question'])
        left, op, right = int(match.group(1)), match.group(2), int(match.group(3))
        answer = left + right if op == '+' else left - right
        return data['captcha_id'], str(answer)

    def test_reset_password_with_security_answer_and_email_code(self):
        captcha_id, captcha_answer = self._captcha_payload()
        code_response = self.client.post(
            '/api/auth/reset-email-code/',
            {
                'account': 'reset_user',
                'security_answer': '测试答案',
                'captcha_id': captcha_id,
                'captcha_answer': captcha_answer,
            },
            format='json',
        )
        self.assertEqual(code_response.status_code, 200)
        demo_code = code_response.json()['demo_email_code']

        captcha_id, captcha_answer = self._captcha_payload()
        reset_response = self.client.post(
            '/api/auth/reset-password/',
            {
                'account': 'reset_user',
                'security_answer': '测试答案',
                'email_code': demo_code,
                'new_password': 'NewPass@123',
                'confirm_password': 'NewPass@123',
                'captcha_id': captcha_id,
                'captcha_answer': captcha_answer,
            },
            format='json',
        )
        self.assertEqual(reset_response.status_code, 200)

        captcha_id, captcha_answer = self._captcha_payload()
        login_response = self.client.post(
            '/api/auth/login/',
            {
                'account': 'reset_user',
                'password': 'NewPass@123',
                'remember_me': True,
                'captcha_id': captcha_id,
                'captcha_answer': captcha_answer,
            },
            format='json',
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertIn('access', login_response.json())
