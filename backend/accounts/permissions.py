from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    message = '仅管理员可执行此操作。'

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        profile = getattr(user, 'profile', None)
        return bool(profile and profile.role == 'admin')
