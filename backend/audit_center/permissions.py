from rest_framework.permissions import BasePermission


class IsAuditorRole(BasePermission):
    message = '仅审计管理员可执行此操作。'

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        profile = getattr(user, 'profile', None)
        return bool(profile and profile.role in ('admin',))
