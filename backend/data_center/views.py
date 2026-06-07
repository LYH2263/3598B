import csv
import io
import logging
import os

from django.http import FileResponse, Http404, HttpResponse
from django.middleware.csrf import get_token
from rest_framework import permissions, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole
from data_center.models import DataTask
from data_center.serializers import (
    DataTaskSerializer,
    ExportRequestSerializer,
    ImportPreviewResultSerializer,
    ImportSubmitSerializer,
    ImportUploadSerializer,
    TaskListQuerySerializer,
    TaskRerunSerializer,
)
from data_center.services.export_service import ExportService
from data_center.services.import_service import IMPORT_HANDLERS, ImportService
from data_center.services.task_service import TaskService

logger = logging.getLogger(__name__)


class DataTypesMetaAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        meta = ExportService.get_data_types_meta()
        return Response(meta)


class TaskListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        query_serializer = TaskListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        q = query_serializer.validated_data

        qs = TaskService.list_tasks(
            task_type=q.get('task_type') or None,
            data_type=q.get('data_type') or None,
            status=q.get('status') or None,
            keyword=q.get('keyword') or None,
        )

        page = int(q.get('page', 1))
        page_size = int(q.get('page_size', 20))
        start = (page - 1) * page_size
        end = start + page_size
        total = qs.count()

        items = qs[start:end]
        serialized = DataTaskSerializer(items, many=True).data

        return Response({
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': serialized,
        })


class TaskStatsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        from django.db.models import Count

        stats = {
            'total': DataTask.objects.count(),
            'by_status': dict(
                DataTask.objects.values_list('status').annotate(count=Count('id')).order_by()
            ),
            'by_task_type': dict(
                DataTask.objects.values_list('task_type').annotate(count=Count('id')).order_by()
            ),
            'running': DataTask.objects.filter(status=DataTask.STATUS_RUNNING).count(),
            'pending': DataTask.objects.filter(status=DataTask.STATUS_SUBMITTED).count(),
        }
        return Response(stats)


class TaskDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, task_id):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        task = DataTask.objects.filter(id=task_id).first()
        if not task:
            return Response({'detail': '任务不存在'}, status=status.HTTP_404_NOT_FOUND)

        data = DataTaskSerializer(task).data
        if task.status in (DataTask.STATUS_SUBMITTED, DataTask.STATUS_RUNNING):
            data['preview'] = task.preview_data or {}
        return Response(data)


class TaskRerunAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        serializer = TaskRerunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task_id = serializer.validated_data['task_id']

        origin_task = DataTask.objects.filter(id=task_id).first()
        if not origin_task:
            return Response({'detail': '原任务不存在'}, status=status.HTTP_404_NOT_FOUND)

        new_task = TaskService.create_task(
            task_type=origin_task.task_type,
            data_type=origin_task.data_type,
            operator=request.user,
            file_name=origin_task.file_name,
            file_hash=origin_task.file_hash,
            file_format=origin_task.file_format,
            params=origin_task.params,
            parent_task=origin_task,
        )

        logger.info(
            '任务重跑: admin=%s origin_task=%s new_task=%s',
            request.user.username, task_id, new_task.id,
        )

        if new_task.task_type == DataTask.TASK_TYPE_IMPORT:
            file_path = TaskService.IMPORT_DIR / (
                origin_task.file_name or f'{origin_task.data_type}_{origin_task.id}.csv'
            )
            # 尝试找存在的导入文件（基于哈希）
            for f in TaskService.IMPORT_DIR.iterdir():
                if origin_task.file_hash and origin_task.file_hash[:16] in f.name:
                    file_path = f
                    break
            if not file_path.exists():
                return Response(
                    {'detail': '原导入文件不存在，无法重跑，请重新上传。'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            ImportService.execute_import(new_task, str(file_path))
        else:
            ExportService.execute_export(new_task)

        return Response({
            'detail': '任务已重新提交执行。',
            'task': DataTaskSerializer(new_task).data,
        })


class TaskResultDownloadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, task_id):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        task = DataTask.objects.filter(id=task_id).first()
        if not task or not task.result_file_path:
            raise Http404('结果文件不存在')

        if not os.path.exists(task.result_file_path):
            raise Http404('结果文件已被清理')

        filename = os.path.basename(task.result_file_path)
        return FileResponse(
            open(task.result_file_path, 'rb'),
            as_attachment=True,
            filename=filename,
        )


class TaskErrorDownloadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, task_id):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        task = DataTask.objects.filter(id=task_id).first()
        if not task or not task.error_file_path:
            raise Http404('错误明细文件不存在')

        if not os.path.exists(task.error_file_path):
            raise Http404('错误明细文件已被清理')

        filename = os.path.basename(task.error_file_path)
        return FileResponse(
            open(task.error_file_path, 'rb'),
            as_attachment=True,
            filename=filename,
        )


class TemplateDownloadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, data_type):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        handler = IMPORT_HANDLERS.get(data_type)
        if not handler:
            return Response({'detail': '不支持的数据类型'}, status=status.HTTP_400_BAD_REQUEST)

        labels = handler.field_labels()
        headers = handler.all_fields()
        header_row = [labels.get(h, h) for h in headers]

        sample_rows = self._get_sample_rows(data_type, headers)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(header_row)
        for row in sample_rows:
            writer.writerow(row)

        response = HttpResponse(output.getvalue().encode('utf-8-sig'), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="template_{data_type}.csv"'
        return response

    @staticmethod
    def _get_sample_rows(data_type, headers):
        samples = {
            'users': [
                ['student001', '20240001', 'student001@example.com', '13800138001', 'student', '12345678'],
                ['admin001', '', 'admin@example.com', '13900139001', 'admin', 'Admin@123'],
            ],
            'recharges': [
                ['student001', '20240001', '100.00', 'alipay', 'admin', '线下充值', 'RC202601010001'],
                ['student002', '20240002', '50.00', 'wechat', '', '', 'RC202601010002'],
            ],
            'consumptions': [
                ['student001', '20240001', 'water', '5.5', '3.50', '125.5', 'admin', '2026年1月水费'],
                ['student002', '20240002', 'electricity', '30.0', '0.60', '580.0', '', '2026年1月电费'],
            ],
            'utility_bills': [
                ['student001', '20240001', 'water', '2026-01-01', '2026-01-31', '19.25', '2026-02-28', '5.5', '3.50', '120.0', '125.5', 'pending', 'admin', '1月水费单'],
            ],
        }
        return samples.get(data_type, [])


class ImportUploadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        serializer = ImportUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data_type = serializer.validated_data['data_type']
        file_format = serializer.validated_data.get('file_format') or DataTask.FORMAT_CSV

        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({'detail': '请上传文件'}, status=status.HTTP_400_BAD_REQUEST)

        if uploaded_file.name.lower().endswith('.xlsx'):
            file_format = DataTask.FORMAT_XLSX
        elif uploaded_file.name.lower().endswith('.csv'):
            file_format = DataTask.FORMAT_CSV

        file_hash = TaskService.compute_file_hash(uploaded_file)
        dup_task = TaskService.find_duplicate_import_task(file_hash, data_type)

        saved_path = TaskService.save_uploaded_file(uploaded_file, file_hash, data_type)

        task = TaskService.create_task(
            task_type=DataTask.TASK_TYPE_IMPORT,
            data_type=data_type,
            operator=request.user,
            file_name=uploaded_file.name,
            file_hash=file_hash,
            file_format=file_format,
        )

        preview = ImportService.preview(task, saved_path)
        task.preview_data = preview
        task.save(update_fields=['preview_data'])

        logger.info(
            '导入文件上传: admin=%s data_type=%s file=%s hash=%s rows=%s errors=%s',
            request.user.username, data_type, uploaded_file.name,
            file_hash[:16], preview['total_rows'], preview['error_count'],
        )

        result = {
            'task_id': task.id,
            'total_rows': preview['total_rows'],
            'error_count': preview['error_count'],
            'warning_count': preview['warning_count'],
            'headers': preview['headers'],
            'field_labels': preview['field_labels'],
            'sample_data': preview['sample_data'],
            'all_rows': preview['rows'],
            'duplicate_task': None,
        }
        if dup_task:
            result['duplicate_task'] = {
                'id': dup_task.id,
                'status': dup_task.status,
                'status_display': dup_task.get_status_display(),
                'created_at': dup_task.created_at,
            }

        return Response(ImportPreviewResultSerializer(result).data)


class ImportSubmitAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        serializer = ImportSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task_id = serializer.validated_data['task_id']
        corrected_rows = serializer.validated_data.get('corrected_rows') or {}

        task = DataTask.objects.filter(id=task_id).first()
        if not task:
            return Response({'detail': '任务不存在'}, status=status.HTTP_404_NOT_FOUND)
        if task.task_type != DataTask.TASK_TYPE_IMPORT:
            return Response({'detail': '该任务不是导入任务'}, status=status.HTTP_400_BAD_REQUEST)
        if task.status in (DataTask.STATUS_RUNNING, DataTask.STATUS_SUCCESS):
            return Response({'detail': '该任务已在运行或已完成，请勿重复提交'}, status=status.HTTP_400_BAD_REQUEST)

        file_path = None
        for f in TaskService.IMPORT_DIR.iterdir():
            if task.file_hash and task.file_hash[:16] in f.name:
                file_path = str(f)
                break
        if not file_path:
            return Response({'detail': '找不到上传的文件，请重新上传'}, status=status.HTTP_400_BAD_REQUEST)

        result = ImportService.execute_import(task, file_path, corrected_rows)

        logger.info(
            '导入任务提交执行: admin=%s task_id=%s total=%s success=%s failed=%s skipped=%s',
            request.user.username, task_id,
            result['total'], result['success'], result['failed'], result['skipped'],
        )

        return Response({
            'detail': '导入任务已执行完成。',
            'task': DataTaskSerializer(task).data,
            'result': result,
        })


class ExportSubmitAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        serializer = ExportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task = TaskService.create_task(
            task_type=DataTask.TASK_TYPE_EXPORT,
            data_type=serializer.validated_data['data_type'],
            operator=request.user,
            file_format=serializer.validated_data.get('file_format') or DataTask.FORMAT_CSV,
            params={
                'fields': serializer.validated_data.get('fields') or [],
                'filters': serializer.validated_data.get('filters') or {},
            },
        )

        result = ExportService.execute_export(task)

        logger.info(
            '导出任务提交执行: admin=%s task_id=%s data_type=%s total=%s',
            request.user.username, task.id, task.data_type, result['total'],
        )

        return Response({
            'detail': '导出任务已执行完成。',
            'task': DataTaskSerializer(task).data,
            'result': result,
        })


class ImportRowErrorsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, task_id):
        if not IsAdminRole().has_permission(request, self):
            return Response({'detail': IsAdminRole.message}, status=status.HTTP_403_FORBIDDEN)

        from data_center.models import ImportRowError
        errors = ImportRowError.objects.filter(
            task_id=task_id, is_idempotent_skip=False, imported=False,
        ).order_by('row_number')[:500]

        from data_center.serializers import ImportRowErrorSerializer
        return Response({
            'total': errors.count(),
            'items': ImportRowErrorSerializer(errors, many=True).data,
        })
