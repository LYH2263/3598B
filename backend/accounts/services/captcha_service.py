import random
import uuid

from django.core.cache import cache

CAPTCHA_KEY_PREFIX = 'captcha_challenge:'
CAPTCHA_EXPIRE_SECONDS = 300


class CaptchaService:
    @staticmethod
    def generate_challenge() -> dict:
        left = random.randint(1, 20)
        right = random.randint(1, 20)
        operator = random.choice(['+', '-'])
        if operator == '-' and left < right:
            left, right = right, left
        answer = left + right if operator == '+' else left - right

        captcha_id = uuid.uuid4().hex
        cache.set(f'{CAPTCHA_KEY_PREFIX}{captcha_id}', str(answer), timeout=CAPTCHA_EXPIRE_SECONDS)

        return {
            'captcha_id': captcha_id,
            'question': f'{left} {operator} {right} = ?',
            'expires_in': CAPTCHA_EXPIRE_SECONDS,
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
