import logging

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole
from notices.models import Announcement, UserNotification
from notices.serializers import (
    AnnouncementCreateSerializer,
    AnnouncementSerializer,
    NotificationReadSerializer,
    UserNotificationSerializer,
)
from notices.services import NotificationService

logger = logging.getLogger(__name__)


class AnnouncementListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        include_inactive = request.query_params.get('include_inactive', 'false') == 'true'
        queryset = Announcement.objects.all()
        if not include_inactive or getattr(request.user.profile, 'role', 'student') != 'admin':
            queryset = queryset.filter(is_active=True)

        return Response(AnnouncementSerializer(queryset[:100], many=True).data)

    def post(self, request):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        serializer = AnnouncementCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        announcement = serializer.save()

        push_count = NotificationService.push_announcement(announcement)
        logger.info('Announcement published by %s, pushed to %s users', request.user.username, push_count)

        return Response(
            {
                'announcement': AnnouncementSerializer(announcement).data,
                'push_count': push_count,
            },
            status=status.HTTP_201_CREATED,
        )


class NotificationListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = UserNotification.objects.filter(user=request.user).order_by('-created_at')[:200]
        unread_count = UserNotification.objects.filter(user=request.user, is_read=False).count()
        return Response(
            {
                'unread_count': unread_count,
                'items': UserNotificationSerializer(queryset, many=True).data,
            }
        )


class NotificationReadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = NotificationReadSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response({'detail': '通知状态已更新。', **result})
