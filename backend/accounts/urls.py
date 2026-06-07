from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views import (
    AdminUserDetailAPIView,
    AdminUserListAPIView,
    CaptchaAPIView,
    LoginAPIView,
    MeAPIView,
    PasswordResetAPIView,
    RegisterAPIView,
    RequestResetEmailCodeAPIView,
)

urlpatterns = [
    path('captcha/', CaptchaAPIView.as_view(), name='captcha'),
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('me/', MeAPIView.as_view(), name='me'),
    path('reset-email-code/', RequestResetEmailCodeAPIView.as_view(), name='reset-email-code'),
    path('reset-password/', PasswordResetAPIView.as_view(), name='reset-password'),
    path('admin/users/', AdminUserListAPIView.as_view(), name='admin-users'),
    path('admin/users/<int:user_id>/', AdminUserDetailAPIView.as_view(), name='admin-user-detail'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
]
