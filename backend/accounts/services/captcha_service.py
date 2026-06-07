import random
import uuid

from django.core.cache import cache

from config_center.services.config_service import ConfigService

CAPTCHA_KEY_PREFIX = 'captcha_challenge:'


class CaptchaService:
    @staticmethod
    def _get_expire_seconds() -> int:
        val = ConfigService.get_int('security', 'captcha_expire_seconds', default=300)
        return val if val > 0 else 300

    @staticmethod
    def generate_challenge() -> dict:
        left = random.randint(1, 20)
        right = random.randint(1, 20)
        operator = random.choice(['+', '-'])
        if operator == '-' and left < right:
            left, right = right, left
        answer = left + right if operator == '+' else left - right

        expire_seconds = CaptchaService._get_expire_seconds()
        captcha_id = uuid.uuid4().hex
        cache.set(f'{CAPTCHA_KEY_PREFIX}{captcha_id}', str(answer), timeout=expire_seconds)

        return {
            'captcha_id': captcha_id,
            'question': f'{left} {operator} {right} = ?',
            'expires_in': expire_seconds,
        }

    @staticmethod
    def verify_challenge(captcha_id: str, captcha_answer: str) -> bool:
        if not captcha_id or captcha_answer is None:
            return False

        key = f'{CAPTCHA_KEY_PREFIX}{captcha_id}'
        answer = cache.get(key)
        cache.delete(key)
        if answer is None:
            return False
        return str(captcha_answer).strip() == str(answer)
