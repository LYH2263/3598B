import random
from django.core.cache import cache


class PasswordResetService:
    CODE_TTL_SECONDS = 300
    CACHE_KEY_PREFIX = 'pwd_reset_email_code:'

    @classmethod
    def _cache_key(cls, user_id: int) -> str:
        return f'{cls.CACHE_KEY_PREFIX}{user_id}'

    @classmethod
    def issue_email_code(cls, user) -> str:
        code = f'{random.randint(100000, 999999)}'
        cache.set(cls._cache_key(user.id), code, timeout=cls.CODE_TTL_SECONDS)
        return code

    @classmethod
    def verify_email_code(cls, user, input_code: str) -> bool:
        cache_key = cls._cache_key(user.id)
        actual_code = cache.get(cache_key)
        cache.delete(cache_key)
        return bool(actual_code and str(actual_code) == str(input_code).strip())

    @staticmethod
    def masked_email(email: str) -> str:
        if '@' not in email:
            return '***'
        name, domain = email.split('@', 1)
        if len(name) <= 2:
            return f'{name[0]}***@{domain}'
        return f'{name[0]}***{name[-1]}@{domain}'
