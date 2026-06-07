from django.contrib.auth.models import User
from django.db.models import Q

from accounts.models import Profile


class AuthService:
    @staticmethod
    def find_user_by_account(account: str):
        account = account.strip()

        user = User.objects.filter(username=account).first()
        if user:
            return user

        user = User.objects.filter(email=account).first()
        if user:
            return user

        profile = Profile.objects.select_related('user').filter(
            Q(student_id=account) | Q(phone=account)
        ).first()
        return profile.user if profile else None
