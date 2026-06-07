import logging

from django.db.models import Q
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from activities.models import Activity, ActivityRegistration, ActivityReview
from activities.permissions import IsAdminRole, IsStudentRole
from activities.serializers import (
    ActivityCreateSerializer,
    ActivityDetailSerializer,
    ActivityListSerializer,
    ActivityRegistrationListSerializer,
    ActivityReviewCreateSerializer,
    ActivityReviewSerializer,
    CheckInSerializer,
)
from activities.services.activity_service import ActivityService

logger = logging.getLogger(__name__)


class ActivityListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        keyword = request.query_params.get('keyword', '').strip()
        status_filter = request.query_params.get('status', '').strip()
        is_admin = getattr(request.user.profile, 'role', None) == 'admin'

        ActivityService.update_activity_status()

        queryset = Activity.objects.all()
        if not is_admin:
            queryset = queryset.filter(status__in=[Activity.STATUS_PUBLISHED, Activity.STATUS_ONGOING, Activity.STATUS_ENDED])
        if keyword:
            queryset = queryset.filter(Q(title__icontains=keyword) | Q(location__icontains=keyword))
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        queryset = queryset.select_related('publisher')
        return Response(ActivityListSerializer(queryset[:200], many=True).data)

    def post(self, request):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        serializer = ActivityCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        activity = serializer.save()
        logger.info('Activity created by %s: %s', request.user.username, activity.title)
        return Response(ActivityDetailSerializer(activity).data, status=status.HTTP_201_CREATED)


class ActivityDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk):
        try:
            return Activity.objects.get(pk=pk)
        except Activity.DoesNotExist:
            return None

    def get(self, request, pk):
        activity = self.get_object(pk)
        if not activity:
            return Response({'detail': '活动不存在。'}, status=status.HTTP_404_NOT_FOUND)

        is_admin = getattr(request.user.profile, 'role', None) == 'admin'
        if not is_admin and activity.status == Activity.STATUS_DRAFT:
            return Response({'detail': '活动不存在。'}, status=status.HTTP_404_NOT_FOUND)

        return Response(ActivityDetailSerializer(activity).data)

    def put(self, request, pk):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        activity = self.get_object(pk)
        if not activity:
            return Response({'detail': '活动不存在。'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ActivityCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        activity = serializer.update(activity, serializer.validated_data)
        logger.info('Activity updated by %s: %s', request.user.username, activity.title)
        return Response(ActivityDetailSerializer(activity).data)

    def delete(self, request, pk):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        activity = self.get_object(pk)
        if not activity:
            return Response({'detail': '活动不存在。'}, status=status.HTTP_404_NOT_FOUND)

        activity.delete()
        logger.info('Activity deleted by %s: %s', request.user.username, activity.title)
        return Response({'detail': '活动已删除。'}, status=status.HTTP_204_NO_CONTENT)


class ActivityPublishAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        try:
            activity = Activity.objects.get(pk=pk)
        except Activity.DoesNotExist:
            return Response({'detail': '活动不存在。'}, status=status.HTTP_404_NOT_FOUND)

        if activity.status == Activity.STATUS_DRAFT:
            activity.status = Activity.STATUS_PUBLISHED
            activity.published_at = activity.published_at or __import__('django.utils.timezone', fromlist=['now']).now()
            activity.save()
            logger.info('Activity published by %s: %s', request.user.username, activity.title)

        return Response(ActivityDetailSerializer(activity).data)


class ActivityGenerateCheckInCodeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        try:
            activity = Activity.objects.get(pk=pk)
        except Activity.DoesNotExist:
            return Response({'detail': '活动不存在。'}, status=status.HTTP_404_NOT_FOUND)

        code = activity.generate_check_in_code()
        logger.info('Check-in code generated for activity %s by %s', activity.title, request.user.username)
        return Response({'check_in_code': code, 'activity_id': activity.id})


class ActivityRegistrationListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        is_admin = getattr(request.user.profile, 'role', None) == 'admin'
        activity_id = request.query_params.get('activity_id', '')
        status_filter = request.query_params.get('status', '')

        if is_admin:
            queryset = ActivityRegistration.objects.select_related('user', 'activity', 'user__profile')
            if activity_id:
                queryset = queryset.filter(activity_id=activity_id)
            if status_filter:
                queryset = queryset.filter(status=status_filter)
        else:
            queryset = ActivityRegistration.objects.filter(
                user=request.user,
            ).select_related('activity', 'user__profile')
            if status_filter:
                queryset = queryset.filter(status=status_filter)

        return Response(ActivityRegistrationListSerializer(queryset.order_by('-registered_at')[:200], many=True).data)


class ActivityMyRegistrationsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = ActivityRegistration.objects.filter(
            user=request.user,
        ).select_related('activity', 'user__profile').order_by('-registered_at')
        return Response(ActivityRegistrationListSerializer(queryset, many=True).data)


class ActivityRegisterAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not IsStudentRole().has_permission(request, self):
            return Response({'detail': '仅学生可以报名活动。'}, status=status.HTTP_403_FORBIDDEN)

        try:
            activity = Activity.objects.get(pk=pk)
        except Activity.DoesNotExist:
            return Response({'detail': '活动不存在。'}, status=status.HTTP_404_NOT_FOUND)

        try:
            registration = ActivityService.register_activity(request.user, activity)
            return Response(
                ActivityRegistrationListSerializer(registration).data,
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ActivityCheckInAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not IsStudentRole().has_permission(request, self):
            return Response({'detail': '仅学生可以签到。'}, status=status.HTTP_403_FORBIDDEN)

        try:
            activity = Activity.objects.get(pk=pk)
        except Activity.DoesNotExist:
            return Response({'detail': '活动不存在。'}, status=status.HTTP_404_NOT_FOUND)

        serializer = CheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            registration = ActivityService.check_in_by_code(
                activity,
                serializer.validated_data['check_in_code'],
                request.user,
            )
            return Response(ActivityRegistrationListSerializer(registration).data)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ActivityRegistrationReviewAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        try:
            registration = ActivityRegistration.objects.get(pk=pk)
        except ActivityRegistration.DoesNotExist:
            return Response({'detail': '报名记录不存在。'}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action', '')
        review_remark = request.data.get('review_remark', '')
        if action not in {ActivityRegistration.STATUS_APPROVED, ActivityRegistration.STATUS_REJECTED}:
            return Response({'detail': '非法审核动作。'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            registration = ActivityService.review_registration(
                registration,
                action,
                request.user,
                review_remark,
            )
            return Response(ActivityRegistrationListSerializer(registration).data)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ActivityRegistrationBatchReviewAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        registration_ids = request.data.get('ids', [])
        action = request.data.get('action', '')
        review_remark = request.data.get('review_remark', '')

        if not isinstance(registration_ids, list) or not registration_ids:
            return Response({'detail': '请选择要审核的报名记录。'}, status=status.HTTP_400_BAD_REQUEST)
        if action not in {ActivityRegistration.STATUS_APPROVED, ActivityRegistration.STATUS_REJECTED}:
            return Response({'detail': '非法审核动作。'}, status=status.HTTP_400_BAD_REQUEST)

        updated = ActivityService.batch_review_registrations(
            registration_ids,
            action,
            request.user,
            review_remark,
        )
        logger.info('Batch reviewed %s registrations by %s', updated, request.user.username)
        return Response({'updated_count': updated})


class ActivityReviewListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            activity = Activity.objects.get(pk=pk)
        except Activity.DoesNotExist:
            return Response({'detail': '活动不存在。'}, status=status.HTTP_404_NOT_FOUND)

        reviews = activity.reviews.select_related('user').order_by('-created_at')[:100]
        return Response(ActivityReviewSerializer(reviews, many=True).data)

    def post(self, request, pk):
        if not IsStudentRole().has_permission(request, self):
            return Response({'detail': '仅学生可以评价活动。'}, status=status.HTTP_403_FORBIDDEN)

        try:
            activity = Activity.objects.get(pk=pk)
        except Activity.DoesNotExist:
            return Response({'detail': '活动不存在。'}, status=status.HTTP_404_NOT_FOUND)

        registration = ActivityRegistration.objects.filter(
            activity=activity,
            user=request.user,
            status=ActivityRegistration.STATUS_CHECKED_IN,
        ).first()
        if not registration:
            return Response({'detail': '您未实际参与该活动，不可评价。'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ActivityReviewCreateSerializer(
            data=request.data,
            context={'request': request, 'activity': activity, 'registration': registration},
        )
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        logger.info('Review created by %s for activity %s', request.user.username, activity.title)
        return Response(ActivityReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class ActivityCalendarAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from django.utils.dateparse import parse_date

        start_date = request.query_params.get('start_date', '')
        end_date = request.query_params.get('end_date', '')

        is_admin = getattr(request.user.profile, 'role', None) == 'admin'
        queryset = Activity.objects.all()
        if not is_admin:
            queryset = queryset.filter(status__in=[Activity.STATUS_PUBLISHED, Activity.STATUS_ONGOING, Activity.STATUS_ENDED])

        if start_date:
            s = parse_date(start_date)
            if s:
                from datetime import datetime
                queryset = queryset.filter(end_time__gte=datetime.combine(s, datetime.min.time()))
        if end_date:
            e = parse_date(end_date)
            if e:
                from datetime import datetime
                queryset = queryset.filter(start_time__lte=datetime.combine(e, datetime.max.time()))

        queryset = queryset.order_by('start_time')[:500]
        return Response(ActivityListSerializer(queryset, many=True).data)
