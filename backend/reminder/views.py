import logging

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Count
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole
from accounts.models import Profile
from reminder.models import Reminder, StudentReminderExemption
from reminder.serializers import (
    AdminReminderListQuerySerializer,
    AdminResumeRemindersSerializer,
    AdminStopAllRemindersSerializer,
    AdminTriggerReminderSerializer,
    ReminderHandleSerializer,
    ReminderSerializer,
    ReminderStatsSerializer,
    StudentReminderExemptionSerializer,
)
from reminder.services import ReminderService

logger = logging.getLogger(__name__)


class StudentReminderListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        status_filter = request.query_params.get('status')
        queryset = Reminder.objects.filter(user=request.user)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        queryset = queryset.select_related('handled_by').prefetch_related('events').order_by('-created_at')

        pending_count = Reminder.objects.filter(user=request.user, status=Reminder.STATUS_PENDING).count()

        return Response({
            'pending_count': pending_count,
            'items': ReminderSerializer(queryset[:200], many=True).data,
        })


class StudentReminderHandleAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ReminderHandleSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        reminder = serializer.save()
        return Response({
            'detail': '提醒已标记为已处理。',
            'reminder': ReminderSerializer(reminder).data,
        })


class AdminReminderListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        query_serializer = AdminReminderListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        q = query_serializer.validated_data

        queryset = Reminder.objects.select_related('user', 'handled_by', 'user__profile').prefetch_related('events')

        if q.get('status'):
            queryset = queryset.filter(status=q['status'])
        if q.get('trigger_type'):
            queryset = queryset.filter(trigger_type=q['trigger_type'])
        if q.get('user_id'):
            queryset = queryset.filter(user_id=q['user_id'])
        if q.get('keyword'):
            keyword = q['keyword']
            queryset = queryset.filter(
                models.Q(user__username__icontains=keyword)
                | models.Q(title__icontains=keyword)
                | models.Q(content__icontains=keyword)
            )

        queryset = queryset.order_by('-created_at')

        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        start = (page - 1) * page_size
        end = start + page_size
        total = queryset.count()

        items = queryset[start:end]
        serialized_items = []
        for r in items:
            data = ReminderSerializer(r).data
            data['username'] = r.user.username
            data['student_id'] = getattr(r.user.profile, 'student_id', '')
            serialized_items.append(data)

        return Response({
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': serialized_items,
        })


class AdminReminderStatsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        total_pending = Reminder.objects.filter(status=Reminder.STATUS_PENDING).count()
        total_handled = Reminder.objects.filter(status=Reminder.STATUS_HANDLED).count()
        total_stopped = Reminder.objects.filter(status=Reminder.STATUS_STOPPED).count()
        total_resolved_auto = Reminder.objects.filter(status=Reminder.STATUS_RESOLVED_AUTO).count()

        by_trigger = dict(
            Reminder.objects.values_list('trigger_type')
            .annotate(count=Count('id'))
            .order_by()
        )
        by_channel = dict(
            Reminder.objects.filter(status=Reminder.STATUS_PENDING)
            .values_list('current_channel')
            .annotate(count=Count('id'))
            .order_by()
        )

        exempted_count = StudentReminderExemption.objects.filter(is_exempted=True).count()

        stats = {
            'total_pending': total_pending,
            'total_handled': total_handled,
            'total_stopped': total_stopped,
            'total_resolved_auto': total_resolved_auto,
            'by_trigger_type': by_trigger,
            'by_channel': by_channel,
            'exempted_count': exempted_count,
        }

        serializer = ReminderStatsSerializer(stats)
        return Response(serializer.data)


class AdminTriggerReminderAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        serializer = AdminTriggerReminderSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        reminder = serializer.save()

        logger.info(
            '管理员手动触发催缴: admin=%s user_id=%s reminder_id=%s',
            request.user.username,
            request.data.get('user_id'),
            reminder.id,
        )

        return Response({
            'detail': '催缴提醒已发送。',
            'reminder': ReminderSerializer(reminder).data,
        }, status=status.HTTP_201_CREATED)


class AdminStopAllRemindersAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        serializer = AdminStopAllRemindersSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        exemption = serializer.save()

        return Response({
            'detail': '已停止对该学生的所有催缴。',
            'exemption': StudentReminderExemptionSerializer(exemption).data,
        })


class AdminResumeRemindersAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        serializer = AdminResumeRemindersSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        exemption = serializer.save()

        return Response({
            'detail': '已恢复对该学生的催缴。',
            'exemption': StudentReminderExemptionSerializer(exemption).data,
        })


class AdminReminderScanAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        result = ReminderService.scan_all_students()
        esc_result = ReminderService.escalate_reminders()
        resolve_result = ReminderService.auto_resolve_reminders()

        logger.info(
            '管理员手动触发催缴扫描: admin=%s result=%s',
            request.user.username,
            {**result, **esc_result, **resolve_result},
        )

        return Response({
            'detail': '催缴扫描执行完成。',
            'scan': result,
            'escalate': esc_result,
            'resolve': resolve_result,
        })


class AdminExemptionListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        only_exempted = request.query_params.get('only_exempted', 'false') == 'true'
        queryset = StudentReminderExemption.objects.select_related('user', 'exempted_by')

        if only_exempted:
            queryset = queryset.filter(is_exempted=True)

        queryset = queryset.order_by('-updated_at')
        return Response(StudentReminderExemptionSerializer(queryset[:200], many=True).data)
