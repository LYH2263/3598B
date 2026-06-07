import csv
import logging
from decimal import Decimal
from datetime import datetime

from django.contrib.auth.models import User
from django.db.models import Q

from billing.models import (
    ConsumptionRecord,
    RechargeRecord,
    UtilityBill,
)
from data_center.models import DataTask
from data_center.services.task_service import TaskService

logger = logging.getLogger(__name__)


class BaseExportHandler:
    name = 'base'
    model = None
    queryset = None

    @classmethod
    def get_available_fields(cls):
        return []

    @classmethod
    def get_field_labels(cls):
        return {}

    @classmethod
    def get_filter_options(cls):
        return []

    @classmethod
    def build_queryset(cls, filters: dict):
        return cls.queryset.all()

    @classmethod
    def serialize_row(cls, obj, fields: list) -> dict:
        row = {}
        for f in fields:
            val = getattr(obj, f, '')
            if isinstance(val, Decimal):
                val = str(val)
            elif hasattr(val, 'strftime'):
                val = val.strftime('%Y-%m-%d %H:%M:%S')
            elif val is None:
                val = ''
            row[f] = str(val)
        return row


class UserExportHandler(BaseExportHandler):
    name = 'users'
    model = User

    @classmethod
    def get_available_fields(cls):
        return [
            'id', 'username', 'email', 'date_joined', 'is_active',
            'profile__student_id', 'profile__phone', 'profile__role',
            'wallet__balance', 'wallet__is_frozen',
        ]

    @classmethod
    def get_field_labels(cls):
        return {
            'id': '用户ID',
            'username': '用户名',
            'email': '邮箱',
            'date_joined': '注册时间',
            'is_active': '是否激活',
            'profile__student_id': '学号',
            'profile__phone': '手机号',
            'profile__role': '角色',
            'wallet__balance': '钱包余额',
            'wallet__is_frozen': '是否冻结',
        }

    @classmethod
    def get_filter_options(cls):
        return [
            {'key': 'role', 'label': '角色', 'type': 'choice', 'options': [('student', '学生'), ('admin', '管理员')]},
            {'key': 'keyword', 'label': '关键字(用户名/学号)', 'type': 'text'},
            {'key': 'is_frozen', 'label': '是否冻结', 'type': 'choice', 'options': [('true', '已冻结'), ('false', '正常')]},
            {'key': 'date_from', 'label': '注册开始日期', 'type': 'date'},
            {'key': 'date_to', 'label': '注册结束日期', 'type': 'date'},
        ]

    @classmethod
    def build_queryset(cls, filters: dict):
        qs = User.objects.select_related('profile', 'wallet').all()
        role = filters.get('role')
        if role:
            qs = qs.filter(profile__role=role)
        keyword = filters.get('keyword')
        if keyword:
            qs = qs.filter(
                Q(username__icontains=keyword) | Q(profile__student_id__icontains=keyword)
            )
        frozen = filters.get('is_frozen')
        if frozen == 'true':
            qs = qs.filter(wallet__is_frozen=True)
        elif frozen == 'false':
            qs = qs.filter(wallet__is_frozen=False)
        date_from = filters.get('date_from')
        if date_from:
            qs = qs.filter(date_joined__gte=date_from)
        date_to = filters.get('date_to')
        if date_to:
            qs = qs.filter(date_joined__lte=date_to + ' 23:59:59')
        return qs

    @classmethod
    def serialize_row(cls, obj, fields: list) -> dict:
        row = {}
        for f in fields:
            if f.startswith('profile__'):
                field_name = f.replace('profile__', '')
                val = getattr(getattr(obj, 'profile', None), field_name, '')
            elif f.startswith('wallet__'):
                field_name = f.replace('wallet__', '')
                val = getattr(getattr(obj, 'wallet', None), field_name, '')
            else:
                val = getattr(obj, f, '')
            if isinstance(val, Decimal):
                val = str(val)
            elif hasattr(val, 'strftime'):
                val = val.strftime('%Y-%m-%d %H:%M:%S')
            elif val is None:
                val = ''
            row[f] = str(val)
        return row


class RechargeExportHandler(BaseExportHandler):
    name = 'recharges'
    model = RechargeRecord

    @classmethod
    def get_available_fields(cls):
        return [
            'id', 'user__username', 'user__profile__student_id', 'amount',
            'channel', 'operator', 'remark', 'created_at',
        ]

    @classmethod
    def get_field_labels(cls):
        return {
            'id': '记录ID',
            'user__username': '用户名',
            'user__profile__student_id': '学号',
            'amount': '金额',
            'channel': '渠道',
            'operator': '操作人',
            'remark': '备注',
            'created_at': '创建时间',
        }

    @classmethod
    def get_filter_options(cls):
        return [
            {'key': 'channel', 'label': '渠道', 'type': 'choice', 'options': [('alipay', '支付宝'), ('wechat', '微信'), ('bank', '银行卡')]},
            {'key': 'keyword', 'label': '用户名/学号', 'type': 'text'},
            {'key': 'amount_min', 'label': '最小金额', 'type': 'number'},
            {'key': 'amount_max', 'label': '最大金额', 'type': 'number'},
            {'key': 'date_from', 'label': '开始日期', 'type': 'date'},
            {'key': 'date_to', 'label': '结束日期', 'type': 'date'},
        ]

    @classmethod
    def build_queryset(cls, filters: dict):
        qs = RechargeRecord.objects.select_related('user', 'user__profile').all()
        channel = filters.get('channel')
        if channel:
            qs = qs.filter(channel=channel)
        keyword = filters.get('keyword')
        if keyword:
            qs = qs.filter(
                Q(user__username__icontains=keyword) | Q(user__profile__student_id__icontains=keyword)
            )
        amt_min = filters.get('amount_min')
        if amt_min:
            qs = qs.filter(amount__gte=amt_min)
        amt_max = filters.get('amount_max')
        if amt_max:
            qs = qs.filter(amount__lte=amt_max)
        date_from = filters.get('date_from')
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        date_to = filters.get('date_to')
        if date_to:
            qs = qs.filter(created_at__lte=date_to + ' 23:59:59')
        return qs

    @classmethod
    def serialize_row(cls, obj, fields: list) -> dict:
        row = {}
        for f in fields:
            parts = f.split('__')
            val = obj
            for p in parts:
                val = getattr(val, p, '')
                if val is None:
                    break
            if isinstance(val, Decimal):
                val = str(val)
            elif hasattr(val, 'strftime'):
                val = val.strftime('%Y-%m-%d %H:%M:%S')
            elif val is None:
                val = ''
            row[f] = str(val)
        return row


class ConsumptionExportHandler(BaseExportHandler):
    name = 'consumptions'
    model = ConsumptionRecord

    @classmethod
    def get_available_fields(cls):
        return [
            'id', 'user__username', 'user__profile__student_id', 'category',
            'usage', 'unit_price', 'cost_amount', 'meter_value',
            'operator', 'remark', 'created_at',
        ]

    @classmethod
    def get_field_labels(cls):
        return {
            'id': '记录ID',
            'user__username': '用户名',
            'user__profile__student_id': '学号',
            'category': '类型',
            'usage': '用量',
            'unit_price': '单价',
            'cost_amount': '扣费金额',
            'meter_value': '表底',
            'operator': '操作人',
            'remark': '备注',
            'created_at': '创建时间',
        }

    @classmethod
    def get_filter_options(cls):
        return [
            {'key': 'category', 'label': '类型', 'type': 'choice', 'options': [('water', '水费'), ('electricity', '电费')]},
            {'key': 'keyword', 'label': '用户名/学号', 'type': 'text'},
            {'key': 'amount_min', 'label': '最小金额', 'type': 'number'},
            {'key': 'amount_max', 'label': '最大金额', 'type': 'number'},
            {'key': 'date_from', 'label': '开始日期', 'type': 'date'},
            {'key': 'date_to', 'label': '结束日期', 'type': 'date'},
        ]

    @classmethod
    def build_queryset(cls, filters: dict):
        qs = ConsumptionRecord.objects.select_related('user', 'user__profile').all()
        category = filters.get('category')
        if category:
            qs = qs.filter(category=category)
        keyword = filters.get('keyword')
        if keyword:
            qs = qs.filter(
                Q(user__username__icontains=keyword) | Q(user__profile__student_id__icontains=keyword)
            )
        amt_min = filters.get('amount_min')
        if amt_min:
            qs = qs.filter(cost_amount__gte=amt_min)
        amt_max = filters.get('amount_max')
        if amt_max:
            qs = qs.filter(cost_amount__lte=amt_max)
        date_from = filters.get('date_from')
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        date_to = filters.get('date_to')
        if date_to:
            qs = qs.filter(created_at__lte=date_to + ' 23:59:59')
        return qs

    @classmethod
    def serialize_row(cls, obj, fields: list) -> dict:
        row = {}
        for f in fields:
            parts = f.split('__')
            val = obj
            for p in parts:
                val = getattr(val, p, '')
                if val is None:
                    break
            if isinstance(val, Decimal):
                val = str(val)
            elif hasattr(val, 'strftime'):
                val = val.strftime('%Y-%m-%d %H:%M:%S')
            elif val is None:
                val = ''
            row[f] = str(val)
        return row


class UtilityBillExportHandler(BaseExportHandler):
    name = 'utility_bills'
    model = UtilityBill

    @classmethod
    def get_available_fields(cls):
        return [
            'id', 'bill_no', 'user__username', 'user__profile__student_id',
            'category', 'period_start', 'period_end', 'usage', 'unit_price',
            'base_amount', 'late_fee_amount', 'total_amount', 'paid_amount',
            'due_date', 'status', 'operator', 'remark', 'created_at',
        ]

    @classmethod
    def get_field_labels(cls):
        return {
            'id': '账单ID',
            'bill_no': '账单编号',
            'user__username': '用户名',
            'user__profile__student_id': '学号',
            'category': '类型',
            'period_start': '周期开始',
            'period_end': '周期结束',
            'usage': '用量',
            'unit_price': '单价',
            'base_amount': '基础金额',
            'late_fee_amount': '滞纳金',
            'total_amount': '应缴总额',
            'paid_amount': '已缴金额',
            'due_date': '缴费截止',
            'status': '状态',
            'operator': '操作人',
            'remark': '备注',
            'created_at': '创建时间',
        }

    @classmethod
    def get_filter_options(cls):
        return [
            {'key': 'category', 'label': '类型', 'type': 'choice', 'options': [('water', '水费'), ('electricity', '电费')]},
            {'key': 'status', 'label': '状态', 'type': 'choice', 'options': [
                ('pending', '待缴'), ('paid', '已缴'), ('void', '已作废'),
                ('merged', '已合并'), ('overdue', '已逾期'),
            ]},
            {'key': 'keyword', 'label': '用户名/学号/账单号', 'type': 'text'},
            {'key': 'amount_min', 'label': '最小金额', 'type': 'number'},
            {'key': 'amount_max', 'label': '最大金额', 'type': 'number'},
            {'key': 'date_from', 'label': '创建开始日期', 'type': 'date'},
            {'key': 'date_to', 'label': '创建结束日期', 'type': 'date'},
        ]

    @classmethod
    def build_queryset(cls, filters: dict):
        qs = UtilityBill.objects.select_related('user', 'user__profile').all()
        category = filters.get('category')
        if category:
            qs = qs.filter(category=category)
        status = filters.get('status')
        if status:
            qs = qs.filter(status=status)
        keyword = filters.get('keyword')
        if keyword:
            qs = qs.filter(
                Q(user__username__icontains=keyword)
                | Q(user__profile__student_id__icontains=keyword)
                | Q(bill_no__icontains=keyword)
            )
        amt_min = filters.get('amount_min')
        if amt_min:
            qs = qs.filter(total_amount__gte=amt_min)
        amt_max = filters.get('amount_max')
        if amt_max:
            qs = qs.filter(total_amount__lte=amt_max)
        date_from = filters.get('date_from')
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        date_to = filters.get('date_to')
        if date_to:
            qs = qs.filter(created_at__lte=date_to + ' 23:59:59')
        return qs

    @classmethod
    def serialize_row(cls, obj, fields: list) -> dict:
        row = {}
        for f in fields:
            parts = f.split('__')
            val = obj
            for p in parts:
                val = getattr(val, p, '')
                if val is None:
                    break
            if isinstance(val, Decimal):
                val = str(val)
            elif hasattr(val, 'strftime'):
                val = val.strftime('%Y-%m-%d') if f in ('period_start', 'period_end', 'due_date') else val.strftime('%Y-%m-%d %H:%M:%S')
            elif val is None:
                val = ''
            row[f] = str(val)
        return row


EXPORT_HANDLERS = {
    DataTask.DATA_TYPE_USERS: UserExportHandler,
    DataTask.DATA_TYPE_RECHARGES: RechargeExportHandler,
    DataTask.DATA_TYPE_CONSUMPTIONS: ConsumptionExportHandler,
    DataTask.DATA_TYPE_UTILITY_BILLS: UtilityBillExportHandler,
}


class ExportService:
    @staticmethod
    def get_handler(data_type: str):
        handler = EXPORT_HANDLERS.get(data_type)
        if not handler:
            raise ValueError(f'不支持的数据类型: {data_type}')
        return handler

    @staticmethod
    def get_data_types_meta() -> list:
        result = []
        for dt_key, handler in EXPORT_HANDLERS.items():
            label_map = dict(DataTask.DATA_TYPE_CHOICES)
            result.append({
                'key': dt_key,
                'label': label_map.get(dt_key, dt_key),
                'fields': [
                    {'key': f, 'label': handler.get_field_labels().get(f, f)}
                    for f in handler.get_available_fields()
                ],
                'filter_options': handler.get_filter_options(),
                'import_required_fields': [],
                'import_optional_fields': [],
            })
        from data_center.services.import_service import IMPORT_HANDLERS
        for item in result:
            imp_handler = IMPORT_HANDLERS.get(item['key'])
            if imp_handler:
                labels = imp_handler.field_labels()
                item['import_required_fields'] = [
                    {'key': f, 'label': labels.get(f, f)} for f in imp_handler.required_fields
                ]
                item['import_optional_fields'] = [
                    {'key': f, 'label': labels.get(f, f)} for f in imp_handler.optional_fields
                ]
        return result

    @staticmethod
    def execute_export(task: DataTask) -> dict:
        handler = ExportService.get_handler(task.data_type)
        params = task.params or {}
        fields = params.get('fields') or handler.get_available_fields()
        filters = params.get('filters') or {}
        fmt = task.file_format or DataTask.FORMAT_CSV

        TaskService.mark_running(task)
        qs = handler.build_queryset(filters)
        total = qs.count()
        task.total_rows = total
        task.save(update_fields=['total_rows'])

        TaskService.ensure_dirs()
        ts = datetime.now().strftime('%Y%m%d%H%M%S')
        ext = 'xlsx' if fmt == DataTask.FORMAT_XLSX else 'csv'
        fname = f'{task.data_type}_export_{task.id}_{ts}.{ext}'
        full_path = TaskService.EXPORT_DIR / fname

        field_labels = handler.get_field_labels()
        header_labels = [field_labels.get(f, f) for f in fields]

        if fmt == DataTask.FORMAT_XLSX:
            try:
                from openpyxl import Workbook
                wb = Workbook()
                ws = wb.active
                ws.title = task.data_type
                ws.append(header_labels)
                for idx, obj in enumerate(qs.iterator(chunk_size=500), start=1):
                    row = handler.serialize_row(obj, fields)
                    ws.append([row.get(f, '') for f in fields])
                    if idx % 100 == 0:
                        progress = int(idx / total * 90) + 5 if total > 0 else 95
                        TaskService.update_progress(task, progress)
                wb.save(str(full_path))
            except ImportError:
                raise ValueError('系统未安装 openpyxl，请导出为 CSV 格式或联系管理员。')
        else:
            with open(str(full_path), 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(header_labels)
                for idx, obj in enumerate(qs.iterator(chunk_size=500), start=1):
                    row = handler.serialize_row(obj, fields)
                    writer.writerow([row.get(f, '') for f in fields])
                    if idx % 100 == 0:
                        progress = int(idx / total * 90) + 5 if total > 0 else 95
                        TaskService.update_progress(task, progress)

        TaskService.mark_success(
            task,
            result_file_path=str(full_path),
            success_rows=total,
        )
        return {
            'total': total,
            'file_path': str(full_path),
        }
