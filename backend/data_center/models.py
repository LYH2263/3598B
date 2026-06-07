from django.contrib.auth.models import User
from django.db import models


class DataTask(models.Model):
    TASK_TYPE_IMPORT = 'import'
    TASK_TYPE_EXPORT = 'export'

    TASK_TYPE_CHOICES = [
        (TASK_TYPE_IMPORT, '导入'),
        (TASK_TYPE_EXPORT, '导出'),
    ]

    DATA_TYPE_USERS = 'users'
    DATA_TYPE_RECHARGES = 'recharges'
    DATA_TYPE_CONSUMPTIONS = 'consumptions'
    DATA_TYPE_UTILITY_BILLS = 'utility_bills'

    DATA_TYPE_CHOICES = [
        (DATA_TYPE_USERS, '用户'),
        (DATA_TYPE_RECHARGES, '充值记录'),
        (DATA_TYPE_CONSUMPTIONS, '消费记录'),
        (DATA_TYPE_UTILITY_BILLS, '水电账单'),
    ]

    STATUS_SUBMITTED = 'submitted'
    STATUS_RUNNING = 'running'
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'
    STATUS_PARTIAL = 'partial'

    STATUS_CHOICES = [
        (STATUS_SUBMITTED, '提交中'),
        (STATUS_RUNNING, '进行中'),
        (STATUS_SUCCESS, '成功'),
        (STATUS_FAILED, '失败'),
        (STATUS_PARTIAL, '部分成功'),
    ]

    FORMAT_CSV = 'csv'
    FORMAT_XLSX = 'xlsx'

    FORMAT_CHOICES = [
        (FORMAT_CSV, 'CSV'),
        (FORMAT_XLSX, 'XLSX'),
    ]

    task_type = models.CharField(
        max_length=20,
        choices=TASK_TYPE_CHOICES,
        verbose_name='任务类型',
    )
    data_type = models.CharField(
        max_length=30,
        choices=DATA_TYPE_CHOICES,
        verbose_name='数据类型',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_SUBMITTED,
        verbose_name='状态',
    )
    progress_percent = models.IntegerField(
        default=0,
        verbose_name='进度百分比',
    )
    operator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='data_tasks',
        verbose_name='操作人',
    )
    file_name = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='文件名',
    )
    file_hash = models.CharField(
        max_length=64,
        blank=True,
        default='',
        verbose_name='文件哈希（幂等控制）',
        db_index=True,
    )
    file_format = models.CharField(
        max_length=10,
        choices=FORMAT_CHOICES,
        default=FORMAT_CSV,
        verbose_name='文件格式',
    )
    params = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='任务参数（筛选条件、字段选择等）',
    )
    result_file_path = models.CharField(
        max_length=500,
        blank=True,
        default='',
        verbose_name='结果文件路径',
    )
    error_file_path = models.CharField(
        max_length=500,
        blank=True,
        default='',
        verbose_name='错误明细文件路径',
    )
    total_rows = models.IntegerField(
        default=0,
        verbose_name='总行数',
    )
    success_rows = models.IntegerField(
        default=0,
        verbose_name='成功行数',
    )
    skipped_rows = models.IntegerField(
        default=0,
        verbose_name='跳过行数（幂等）',
    )
    failed_rows = models.IntegerField(
        default=0,
        verbose_name='失败行数',
    )
    error_message = models.TextField(
        blank=True,
        default='',
        verbose_name='错误信息',
    )
    preview_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='预校验预览数据',
    )
    parent_task = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rerun_tasks',
        verbose_name='重跑来源任务',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间',
    )
    finished_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='完成时间',
    )

    class Meta:
        db_table = 'data_tasks'
        ordering = ['-created_at']
        verbose_name = '数据任务'
        verbose_name_plural = '数据任务'

    def __str__(self) -> str:
        return f'{self.get_task_type_display()}-{self.get_data_type_display()}-{self.id}'


class ImportRowError(models.Model):
    task = models.ForeignKey(
        DataTask,
        on_delete=models.CASCADE,
        related_name='row_errors',
        verbose_name='所属任务',
    )
    row_number = models.IntegerField(
        verbose_name='行号',
    )
    row_data = models.JSONField(
        default=dict,
        verbose_name='原始行数据',
    )
    error_messages = models.JSONField(
        default=list,
        verbose_name='错误信息列表',
    )
    is_corrected = models.BooleanField(
        default=False,
        verbose_name='是否已修正',
    )
    corrected_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='修正后数据',
    )
    is_idempotent_skip = models.BooleanField(
        default=False,
        verbose_name='是否幂等跳过',
    )
    imported = models.BooleanField(
        default=False,
        verbose_name='是否已成功导入',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间',
    )

    class Meta:
        db_table = 'import_row_errors'
        ordering = ['row_number']
        verbose_name = '导入行错误'
        verbose_name_plural = '导入行错误'
        unique_together = [('task', 'row_number')]

    def __str__(self) -> str:
        return f'Task#{self.task_id}-Row{self.row_number}'
