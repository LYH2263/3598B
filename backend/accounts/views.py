import logging
from datetime import timedelta

from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.permissions import IsAdminRole
from accounts.serializers import (
    AdminUserSerializer,
    AdminUserUpdateSerializer,
    LoginSerializer,
    PasswordResetSerializer,
    RegisterSerializer,
    ResetEmailCodeRequestSerializer,
    UserSerializer,
)
from accounts.services.captcha_service import CaptchaService
from accounts.services.reset_service import PasswordResetService
from notices.services import NotificationService

logger = logging.getLogger(__name__)


class CaptchaAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(CaptchaService.generate_challenge())


class RegisterAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info('User registered: %s', user.username)
        return Response({'user': UserSerializer(user).data}, status=status.HTTP_201_CREATED)


class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        remember_me = serializer.validated_data.get('remember_me', False)

        refresh = RefreshToken.for_user(user)
        if not remember_me:
            refresh.set_exp(lifetime=timedelta(hours=12))

        logger.info('User logged in: %s', user.username)
        return Response(
            {
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'remember_me': remember_me,
            }
        )


class MeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({'user': UserSerializer(request.user).data})


class RequestResetEmailCodeAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResetEmailCodeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        code = PasswordResetService.issue_email_code(user)
        masked_email = PasswordResetService.masked_email(user.email)

        NotificationService.create_user_notification(
            user=user,
            title='密码重置邮箱验证码',
            content=f'您的密码重置验证码为：{code}，5分钟内有效。',
            notice_type='security',
        )

        logger.info('Reset email code issued for user: %s', user.username)
        return Response(
            {
                'detail': f'验证码已发送到邮箱 {masked_email}（演示环境可直接使用返回验证码）。',
                'masked_email': masked_email,
                'demo_email_code': code,
                'expires_in': PasswordResetService.CODE_TTL_SECONDS,
            }
        )


class PasswordResetAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        NotificationService.create_user_notification(
            user=user,
            title='密码变更提醒',
            content='您的账号密码已重置。如果不是本人操作，请立即联系管理员。',
            notice_type='security',
        )

        logger.info('Password reset: %s', user.username)
        return Response({'detail': '密码重置成功，请使用新密码登录。'})


class AdminUserListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get(self, request):
        keyword = request.query_params.get('keyword', '').strip()
        role = request.query_params.get('role', '').strip()
        is_active = request.query_params.get('is_active', '').strip()

        queryset = User.objects.select_related('profile', 'wallet').all().order_by('-date_joined')

        if keyword:
            queryset = queryset.filter(
                Q(username__icontains=keyword)
                | Q(email__icontains=keyword)
                | Q(profile__student_id__icontains=keyword)
                | Q(profile__phone__icontains=keyword)
            )
        if role:
            queryset = queryset.filter(profile__role=role)
        if is_active in {'true', 'false'}:
            queryset = queryset.filter(is_active=(is_active == 'true'))

        return Response(AdminUserSerializer(queryset[:200], many=True).data)


class AdminUserDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def patch(self, request, user_id: int):
        user = User.objects.select_related('profile').filter(id=user_id).first()
        if not user:
            return Response({'detail': '用户不存在。'}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminUserUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.update(user, serializer.validated_data)

        NotificationService.create_user_notification(
            user=user,
            title='账号状态变更提醒',
            content='管理员已更新您的账号角色或启用状态。',
            notice_type='system',
        )

        logger.info('Admin %s updated user %s', request.user.username, user.username)
        return Response({'user': AdminUserSerializer(user).data})
