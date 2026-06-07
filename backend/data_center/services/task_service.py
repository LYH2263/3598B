import hashlib
import io
import os
import csv
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone

from data_center.models import DataTask, ImportRowError


class TaskService:
    EXPORT_DIR = Path(getattr(settings, 'MEDIA_ROOT', Path(__file__).resolve().parent.parent.parent / 'media')) / 'data_center' / 'exports'
    IMPORT_DIR = Path(getattr(settings, 'MEDIA_ROOT', Path(__file__).resolve().parent.parent.parent / 'media')) / 'data_center' / 'imports'
    TEMPLATE_DIR = Path(__file__).resolve().parent / 'templates'

    @classmethod
    def ensure_dirs(cls):
        for d in [cls.EXPORT_DIR, cls.IMPORT_DIR]:
            d.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def create_task(*, task_type: str, data_type: str, operator: User, **kwargs) -> DataTask:
        return DataTask.objects.create(
            task_type=task_type,
            data_type=data_type,
            operator=operator,
            **{k: v for k, v in kwargs.items() if v is not None},
        )

    @staticmethod
    def update_progress(task: DataTask, percent: int, **kwargs):
        task.progress_percent = min(100, max(0, percent))
        for k, v in kwargs.items():
            setattr(task, k, v)
        task.save(update_fields=['progress_percent', *kwargs.keys(), 'updated_at'])

    @staticmethod
    def mark_running(task: DataTask):
        task.status = DataTask.STATUS_RUNNING
        task.progress_percent = 5
        task.save(update_fields=['status', 'progress_percent', 'updated_at'])

    @staticmethod
    def mark_success(task: DataTask, **kwargs):
        task.status = DataTask.STATUS_SUCCESS
        task.progress_percent = 100
        task.finished_at = timezone.now()
        for k, v in kwargs.items():
            setattr(task, k, v)
        task.save(update_fields=['status', 'progress_percent', 'finished_at', *kwargs.keys(), 'updated_at'])

    @staticmethod
    def mark_partial(task: DataTask, **kwargs):
        task.status = DataTask.STATUS_PARTIAL
        task.progress_percent = 100
        task.finished_at = timezone.now()
        for k, v in kwargs.items():
            setattr(task, k, v)
        task.save(update_fields=['status', 'progress_percent', 'finished_at', *kwargs.keys(), 'updated_at'])

    @staticmethod
    def mark_failed(task: DataTask, error_message: str = ''):
        task.status = DataTask.STATUS_FAILED
        task.error_message = error_message
        task.finished_at = timezone.now()
        task.save(update_fields=['status', 'error_message', 'finished_at', 'updated_at'])

    @staticmethod
    def compute_file_hash(file_obj) -> str:
        hasher = hashlib.sha256()
        file_obj.seek(0)
        for chunk in iter(lambda: file_obj.read(8192), b''):
            hasher.update(chunk)
        file_obj.seek(0)
        return hasher.hexdigest()

    @staticmethod
    def save_uploaded_file(file_obj, file_hash: str, data_type: str) -> str:
        TaskService.ensure_dirs()
        ext = os.path.splitext(file_obj.name)[1].lower() or '.csv'
        safe_name = f'{data_type}_{file_hash[:16]}_{datetime.now().strftime("%Y%m%d%H%M%S")}{ext}'
        full_path = TaskService.IMPORT_DIR / safe_name
        with open(full_path, 'wb') as f:
            file_obj.seek(0)
            for chunk in file_obj.chunks():
                f.write(chunk)
        return str(full_path)

    @staticmethod
    def list_tasks(operator=None, task_type=None, data_type=None, status=None, keyword=None):
        qs = DataTask.objects.select_related('operator').prefetch_related('row_errors')
        if operator and not (operator.profile and operator.profile.role == 'admin'):
            qs = qs.filter(operator=operator)
        if task_type:
            qs = qs.filter(task_type=task_type)
        if data_type:
            qs = qs.filter(data_type=data_type)
        if status:
            qs = qs.filter(status=status)
        if keyword:
            qs = qs.filter(file_name__icontains=keyword)
        return qs

    @staticmethod
    def find_duplicate_import_task(file_hash: str, data_type: str):
        return DataTask.objects.filter(
            task_type=DataTask.TASK_TYPE_IMPORT,
            data_type=data_type,
            file_hash=file_hash,
            status__in=[DataTask.STATUS_SUCCESS, DataTask.STATUS_PARTIAL, DataTask.STATUS_RUNNING],
        ).order_by('-created_at').first()

    @staticmethod
    def save_csv_result(file_name_prefix: str, rows: list, headers: list, is_error: bool = False) -> str:
        TaskService.ensure_dirs()
        ts = datetime.now().strftime('%Y%m%d%H%M%S')
        category = 'errors' if is_error else 'results'
        fname = f'{file_name_prefix}_{category}_{ts}.csv'
        full_path = TaskService.EXPORT_DIR / fname
        with open(full_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for row in rows:
                writer.writerow([row.get(h, '') for h in headers])
        return str(full_path)
