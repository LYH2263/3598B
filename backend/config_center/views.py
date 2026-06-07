from django.db import models
from django.db.models import Count
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole
from config_center.models import Campus, ConfigChangeLog
from config_center.serializers import (
    CampusSerializer,
    CampusSimpleSerializer,
    ConfigChangeLogSerializer,
    ConfigItemDetailSerializer,
    ConfigUpdateSerializer,
)
from config_center.services.config_service import ConfigService


class CampusListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get(self, request):
        keyword = request.query_params.get('keyword', '').strip()
        only_active = request.query_params.get('only_active', '').strip()

        qs = Campus.objects.annotate(user_count=Count('profiles')).order_by('code')
        if keyword:
            qs = qs.filter(
                models.Q(name__icontains=keyword)
                | models.Q(code__icontains=keyword)
                | models.Q(address__icontains=keyword)
            )
        if only_active in {'true', 'false'}:
            qs = qs.filter(is_active=(only_active == 'true'))

        return Response(CampusSerializer(qs, many=True).data)

    def post(self, request):
        serializer = CampusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        campus = serializer.save()
        return Response(CampusSerializer(campus).data, status=status.HTTP_201_CREATED)


class CampusDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def _get_campus(self, pk):
        return Campus.objects.filter(pk=pk).first()

    def get(self, request, pk):
        campus = self._get_campus(pk)
        if not campus:
            return Response({'detail': '校区不存在。'}, status=status.HTTP_404_NOT_FOUND)
        return Response(CampusSerializer(campus).data)

    def put(self, request, pk):
        campus = self._get_campus(pk)
        if not campus:
            return Response({'detail': '校区不存在。'}, status=status.HTTP_404_NOT_FOUND)
        serializer = CampusSerializer(campus, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        campus = serializer.save()
        return Response(CampusSerializer(campus).data)

    def delete(self, request, pk):
        campus = self._get_campus(pk)
        if not campus:
            return Response({'detail': '校区不存在。'}, status=status.HTTP_404_NOT_FOUND)
        user_count = campus.profiles.count()
        if user_count > 0:
            return Response(
                {'detail': f'该校区下还有 {user_count} 个用户，无法删除。请先迁移用户。'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        campus.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CampusSimpleListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = Campus.objects.filter(is_active=True).order_by('code')
        return Response(CampusSimpleSerializer(qs, many=True).data)


class ConfigGroupListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get(self, request):
        groups = ConfigService.list_groups()
        return Response(groups)


class ConfigListByGroupAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get(self, request, group):
        campus_id = request.query_params.get('campus_id', '').strip()
        campus_obj = None
        if campus_id:
            try:
                campus_id = int(campus_id)
                campus_obj = Campus.objects.filter(id=campus_id).first()
            except ValueError:
                campus_id = None

        items = ConfigService.list_configs_by_group(group, campus_obj)
        serializer = ConfigItemDetailSerializer(items, many=True)
        return Response(serializer.data)


class ConfigUpdateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def post(self, request, group, key):
        serializer = ConfigUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        campus = None
        campus_id = serializer.validated_data.get('campus_id')
        if campus_id:
            campus = Campus.objects.filter(id=campus_id).first()
            if not campus:
                return Response({'detail': '校区不存在。'}, status=status.HTTP_400_BAD_REQUEST)

        value_obj, err = ConfigService.set_value(
            group=group,
            key=key,
            value=serializer.validated_data['value'],
            campus=campus,
            changed_by=request.user,
            remark=serializer.validated_data.get('remark', ''),
        )
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'detail': '配置已更新。'})


class ConfigChangeLogListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get(self, request):
        group = request.query_params.get('group', '').strip()
        key = request.query_params.get('key', '').strip()
        campus_id_raw = request.query_params.get('campus_id', '').strip()
        campus_id = None
        if campus_id_raw:
            try:
                campus_id = int(campus_id_raw)
            except ValueError:
                campus_id = None

        logs = ConfigService.get_change_logs(
            group=group or None,
            key=key or None,
            campus_id=campus_id,
            limit=200,
        )
        return Response(ConfigChangeLogSerializer(logs, many=True).data)


class ConfigInitAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def post(self, request):
        count = ConfigService.ensure_default_configs()
        return Response({'created_count': count, 'detail': f'已初始化 {count} 个默认配置项。'})

