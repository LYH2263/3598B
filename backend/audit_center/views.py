import csv
import io
import json
from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole
from audit_center.models import AuditLog
from audit_center.serializers import (
    AuditExportQuerySerializer,
    AuditLogListQuerySerializer,
    AuditLogSerializer,
    AuditReportQuerySerializer,
    AuditTimelineQuerySerializer,
)
from audit_center.services.anomaly_service import AnomalyDetectionService
from audit_center.services.audit_service import AuditService


class AuditLogListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def _build_queryset(self, validated: dict):
        qs = AuditLog.objects.all().order_by('-created_at')

        if validated.get('category'):
            qs = qs.filter(category=validated['category'])
        if validated.get('action'):
            qs = qs.filter(action=validated['action'])
        if validated.get('status'):
            qs = qs.filter(status=validated['status'])
        if validated.get('operator_id'):
            qs = qs.filter(operator_id=validated['operator_id'])
        if validated.get('operator_username'):
            qs = qs.filter(operator_username__icontains=validated['operator_username'])
        if validated.get('target_type'):
            qs = qs.filter(target_type__icontains=validated['target_type'])
        if validated.get('target_id'):
            qs = qs.filter(target_id=validated['target_id'])
        if validated.get('ip_address'):
            qs = qs.filter(ip_address__icontains=validated['ip_address'])
        if validated.get('is_suspicious') is not None:
            qs = qs.filter(is_suspicious=validated['is_suspicious'])
        if validated.get('start_date'):
            qs = qs.filter(created_at__date__gte=validated['start_date'])
        if validated.get('end_date'):
            qs = qs.filter(created_at__date__lte=validated['end_date'])

        keyword = validated.get('keyword', '').strip()
        if keyword:
            qs = qs.filter(
                Q(operator_username__icontains=keyword)
                | Q(target_display__icontains=keyword)
                | Q(target_id__icontains=keyword)
                | Q(remark__icontains=keyword)
                | Q(ip_address__icontains=keyword)
            )

        return qs

    def get(self, request):
        serializer = AuditLogListQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        q = serializer.validated_data

        qs = self._build_queryset(q)

        total = qs.count()
        page = q['page']
        page_size = q['page_size']
        start = (page - 1) * page_size
        end = start + page_size

        items = qs[start:end]
        data = AuditLogSerializer(items, many=True).data

        return Response({
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': data,
        })


class AuditLogDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get(self, request, pk):
        log = AuditLog.objects.filter(pk=pk).first()
        if not log:
            return Response({'detail': '审计日志不存在。'}, status=status.HTTP_404_NOT_FOUND)
        return Response(AuditLogSerializer(log).data)


class AuditTimelineAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get(self, request):
        serializer = AuditTimelineQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        q = serializer.validated_data

        qs = AuditLog.objects.all().order_by('-created_at')

        if q.get('user_id'):
            qs = qs.filter(
                Q(operator_id=q['user_id']) | Q(target_id=str(q['user_id']), target_type__icontains='user')
            )
        if q.get('target_type'):
            qs = qs.filter(target_type__icontains=q['target_type'])
        if q.get('target_id'):
            qs = qs.filter(target_id=q['target_id'])
        if q.get('start_date'):
            qs = qs.filter(created_at__date__gte=q['start_date'])
        if q.get('end_date'):
            qs = qs.filter(created_at__date__lte=q['end_date'])

        items = qs[:q['limit']]
        return Response({
            'items': AuditLogSerializer(items, many=True).data,
            'count': len(items),
        })


class AuditReplayAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get(self, request):
        mode = request.query_params.get('mode', 'user').strip()
        target_id = request.query_params.get('target_id', '').strip()
        target_type = request.query_params.get('target_type', '').strip()

        if not target_id:
            return Response({'detail': '请指定 target_id'}, status=status.HTTP_400_BAD_REQUEST)

        qs = AuditLog.objects.all()

        if mode == 'user':
            qs = qs.filter(
                Q(operator_id=target_id) | Q(target_id=target_id, target_type__icontains='user')
            )
        else:
            if target_type:
                qs = qs.filter(target_type__icontains=target_type)
            qs = qs.filter(target_id=target_id)

        qs = qs.order_by('created_at')

        items = list(qs[:200])

        timeline = []
        for log in items:
            timeline.append({
                'id': log.id,
                'time': log.created_at.isoformat(),
                'operator': log.operator_username,
                'action': log.get_action_display(),
                'category': log.get_category_display(),
                'target': log.target_display,
                'status': log.get_status_display(),
                'before': log.before_data,
                'after': log.after_data,
                'remark': log.remark,
                'is_suspicious': log.is_suspicious,
            })

        return Response({
            'mode': mode,
            'target_id': target_id,
            'target_type': target_type,
            'timeline': timeline,
            'count': len(timeline),
        })


class AuditReportAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get(self, request):
        serializer = AuditReportQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        q = serializer.validated_data

        now = timezone.now()
        period = q.get('period', 'week')

        if q.get('start_date'):
            start_date = q['start_date']
        else:
            start_date = now - timedelta(days=7 if period == 'week' else 30)

        if q.get('end_date'):
            end_date = q['end_date']
        else:
            end_date = now.date()

        qs = AuditLog.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)

        total_count = qs.count()

        by_category = []
        cat_map = dict(AuditLog.CATEGORY_CHOICES)
        for row in qs.values('category').annotate(count=Count('id')).order_by('-count'):
            by_category.append({
                'category': row['category'],
                'category_display': cat_map.get(row['category'], row['category']),
                'count': row['count'],
            })

        by_action = []
        act_map = dict(AuditLog.ACTION_CHOICES)
        for row in qs.values('action').annotate(count=Count('id')).order_by('-count')[:20]:
            by_action.append({
                'action': row['action'],
                'action_display': act_map.get(row['action'], row['action']),
                'count': row['count'],
            })

        by_operator = list(
            qs.values('operator_id', 'operator_username', 'operator_role')
            .annotate(count=Count('id'))
            .order_by('-count')[:20]
        )

        trunc_fn = TruncDate if period == 'week' else TruncWeek
        trend = list(
            qs.annotate(period=trunc_fn('created_at'))
            .values('period')
            .annotate(count=Count('id'))
            .order_by('period')
        )

        for item in trend:
            p = item.get('period')
            item['period'] = p.strftime('%Y-%m-%d') if p and hasattr(p, 'strftime') else str(p) if p else ''

        suspicious = AnomalyDetectionService.get_suspicious_stats(hours=24 * 30)
        suspicious_count = qs.filter(is_suspicious=True).count()

        status_map = dict(AuditLog.STATUS_CHOICES)
        by_status = []
        for row in qs.values('status').annotate(count=Count('id')):
            by_status.append({
                'status': row['status'],
                'status_display': status_map.get(row['status'], row['status']),
                'count': row['count'],
            })

        return Response({
            'period': period,
            'start_date': str(start_date),
            'end_date': str(end_date),
            'summary': {
                'total_count': total_count,
                'suspicious_count': suspicious_count,
                'success_count': qs.filter(status=AuditLog.STATUS_SUCCESS).count(),
                'failed_count': qs.filter(status=AuditLog.STATUS_FAILED).count(),
            },
            'by_category': by_category,
            'by_action': by_action,
            'by_operator': by_operator,
            'by_status': by_status,
            'trend': trend,
            'suspicious': suspicious,
        })


class AuditSuspiciousAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get(self, request):
        hours = int(request.query_params.get('hours', '24'))
        stats = AnomalyDetectionService.get_suspicious_stats(hours=hours)

        start_time = timezone.now() - timedelta(hours=hours)
        items = AuditLog.objects.filter(
            is_suspicious=True,
            created_at__gte=start_time,
        ).order_by('-created_at')[:100]

        return Response({
            'stats': stats,
            'items': AuditLogSerializer(items, many=True).data,
        })


class AuditCategoryMetaAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get(self, request):
        return Response({
            'categories': [
                {'key': k, 'label': v} for k, v in AuditLog.CATEGORY_CHOICES
            ],
            'actions': [
                {'key': k, 'label': v} for k, v in AuditLog.ACTION_CHOICES
            ],
            'statuses': [
                {'key': k, 'label': v} for k, v in AuditLog.STATUS_CHOICES
            ],
        })


class AuditExportAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get(self, request):
        serializer = AuditExportQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        q = serializer.validated_data

        qs = AuditLog.objects.all().order_by('-created_at')

        if q.get('category'):
            qs = qs.filter(category=q['category'])
        if q.get('action'):
            qs = qs.filter(action=q['action'])
        if q.get('status'):
            qs = qs.filter(status=q['status'])
        if q.get('operator_id'):
            qs = qs.filter(operator_id=q['operator_id'])
        if q.get('target_type'):
            qs = qs.filter(target_type__icontains=q['target_type'])
        if q.get('target_id'):
            qs = qs.filter(target_id=q['target_id'])
        if q.get('ip_address'):
            qs = qs.filter(ip_address__icontains=q['ip_address'])
        if q.get('is_suspicious') is not None:
            qs = qs.filter(is_suspicious=q['is_suspicious'])
        if q.get('start_date'):
            qs = qs.filter(created_at__date__gte=q['start_date'])
        if q.get('end_date'):
            qs = qs.filter(created_at__date__lte=q['end_date'])

        keyword = q.get('keyword', '').strip()
        if keyword:
            qs = qs.filter(
                Q(operator_username__icontains=keyword)
                | Q(target_display__icontains=keyword)
                | Q(target_id__icontains=keyword)
                | Q(remark__icontains=keyword)
            )

        items = qs[:10000]

        fmt = q.get('format', 'csv')

        AuditService.log_data_export(request, 'audit_logs', items.count())

        if fmt == 'json':
            response = HttpResponse(content_type='application/json')
            response['Content-Disposition'] = f'attachment; filename="audit_logs_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json"'
            data = AuditLogSerializer(items, many=True).data
            response.write(json.dumps(data, ensure_ascii=False, indent=2, default=str))
            return response

        output = io.StringIO()
        writer = csv.writer(output)
        headers = [
            'ID', '创建时间', '操作人', '操作人角色',
            '分类', '动作', '状态',
            '目标类型', '目标ID', '目标描述',
            '变更前', '变更后',
            'IP地址', '请求路径', '请求方法',
            '耗时(ms)', '错误信息', '备注',
            '是否可疑', '可疑原因', '哈希值',
        ]
        writer.writerow(headers)

        cat_map = dict(AuditLog.CATEGORY_CHOICES)
        act_map = dict(AuditLog.ACTION_CHOICES)
        stat_map = dict(AuditLog.STATUS_CHOICES)

        for log in items:
            writer.writerow([
                log.id,
                log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else '',
                log.operator_username,
                log.operator_role,
                cat_map.get(log.category, log.category),
                act_map.get(log.action, log.action),
                stat_map.get(log.status, log.status),
                log.target_type,
                log.target_id,
                log.target_display,
                json.dumps(log.before_data, ensure_ascii=False) if log.before_data else '',
                json.dumps(log.after_data, ensure_ascii=False) if log.after_data else '',
                log.ip_address or '',
                log.request_path,
                log.request_method,
                log.duration_ms,
                log.error_message,
                log.remark,
                '是' if log.is_suspicious else '否',
                '; '.join(log.suspicious_reasons) if log.suspicious_reasons else '',
                log.hash_value,
            ])

        response = HttpResponse(output.getvalue().encode('utf-8-sig'), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="audit_logs_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        return response


class AuditOverviewAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get(self, request):
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)

        total_logs = AuditLog.objects.count()
        last_24h_count = AuditLog.objects.filter(created_at__gte=last_24h).count()
        last_7d_count = AuditLog.objects.filter(created_at__gte=last_7d).count()

        suspicious_total = AuditLog.objects.filter(is_suspicious=True).count()
        suspicious_24h = AuditLog.objects.filter(is_suspicious=True, created_at__gte=last_24h).count()

        failed_total = AuditLog.objects.filter(status=AuditLog.STATUS_FAILED).count()
        failed_24h = AuditLog.objects.filter(status=AuditLog.STATUS_FAILED, created_at__gte=last_24h).count()

        cat_map = dict(AuditLog.CATEGORY_CHOICES)
        by_category = []
        for row in AuditLog.objects.filter(created_at__gte=last_7d).values('category').annotate(count=Count('id')).order_by('-count'):
            by_category.append({
                'category': row['category'],
                'label': cat_map.get(row['category'], row['category']),
                'count': row['count'],
            })

        recent_logs = AuditLog.objects.all().order_by('-created_at')[:20]

        return Response({
            'summary': {
                'total_logs': total_logs,
                'last_24h_count': last_24h_count,
                'last_7d_count': last_7d_count,
                'suspicious_total': suspicious_total,
                'suspicious_24h': suspicious_24h,
                'failed_total': failed_total,
                'failed_24h': failed_24h,
            },
            'by_category': by_category,
            'recent_logs': AuditLogSerializer(recent_logs, many=True).data,
        })
