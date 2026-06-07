import hashlib
import json

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    CATEGORY_USER = 'user'
    CATEGORY_ROLE = 'role'
    CATEGORY_ORDER = 'order'
    CATEGORY_WALLET = 'wallet'
    CATEGORY_AUTH = 'auth'
    CATEGORY_CONFIG = 'config'
    CATEGORY_DATA = 'data'
    CATEGORY_OTHER = 'other'

    CATEGORY_CHOICES = [
        (CATEGORY_USER, '用户管理'),
        (CATEGORY_ROLE, '角色变更'),
        (CATEGORY_ORDER, '订单操作'),
        (CATEGORY_WALLET, '钱包操作'),
        (CATEGORY_AUTH, '认证安全'),
        (CATEGORY_CONFIG, '配置变更'),
        (CATEGORY_DATA, '数据操作'),
        (CATEGORY_OTHER, '其他操作'),
    ]

    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    ACTION_LOGIN_SUCCESS = 'login_success'
    ACTION_LOGIN_FAILED = 'login_failed'
    ACTION_LOGOUT = 'logout'
    ACTION_PASSWORD_RESET = 'password_reset'
    ACTION_PASSWORD_CHANGE = 'password_change'
    ACTION_APPROVE = 'approve'
    ACTION_REJECT = 'reject'
    ACTION_SUBMIT = 'submit'
    ACTION_FREEZE = 'freeze'
    ACTION_UNFREEZE = 'unfreeze'
    ACTION_EXPORT = 'export'
    ACTION_IMPORT = 'import'
    ACTION_OTHER = 'other'

    ACTION_CHOICES = [
        (ACTION_CREATE, '创建'),
        (ACTION_UPDATE, '更新'),
        (ACTION_DELETE, '删除'),
        (ACTION_LOGIN_SUCCESS, '登录成功'),
        (ACTION_LOGIN_FAILED, '登录失败'),
        (ACTION_LOGOUT, '登出'),
        (ACTION_PASSWORD_RESET, '密码重置'),
        (ACTION_PASSWORD_CHANGE, '密码修改'),
        (ACTION_APPROVE, '审核通过'),
        (ACTION_REJECT, '审核驳回'),
        (ACTION_SUBMIT, '提交'),
        (ACTION_FREEZE, '冻结'),
        (ACTION_UNFREEZE, '解冻'),
        (ACTION_EXPORT, '导出'),
        (ACTION_IMPORT, '导入'),
        (ACTION_OTHER, '其他'),
    ]

    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = [
        (STATUS_SUCCESS, '成功'),
        (STATUS_FAILED, '失败'),
    ]

    operator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_operations',
        verbose_name='操作人',
    )
    operator_username = models.CharField(max_length=150, blank=True, default='', verbose_name='操作人用户名')
    operator_role = models.CharField(max_length=50, blank=True, default='', verbose_name='操作人角色')

    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default=CATEGORY_OTHER, verbose_name='操作分类')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, default=ACTION_OTHER, verbose_name='操作动作')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SUCCESS, verbose_name='操作状态')

    target_type = models.CharField(max_length=100, blank=True, default='', verbose_name='目标对象类型')
    target_id = models.CharField(max_length=100, blank=True, default='', verbose_name='目标对象ID')
    target_display = models.CharField(max_length=255, blank=True, default='', verbose_name='目标对象描述')

    before_data = models.JSONField(default=dict, blank=True, verbose_name='变更前数据摘要')
    after_data = models.JSONField(default=dict, blank=True, verbose_name='变更后数据摘要')

    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP地址')
    user_agent = models.CharField(max_length=512, blank=True, default='', verbose_name='用户代理')
    request_path = models.CharField(max_length=255, blank=True, default='', verbose_name='请求路径')
    request_method = models.CharField(max_length=10, blank=True, default='', verbose_name='请求方法')

    duration_ms = models.IntegerField(default=0, verbose_name='耗时(毫秒)')
    error_message = models.TextField(blank=True, default='', verbose_name='错误信息')
    remark = models.CharField(max_length=500, blank=True, default='', verbose_name='备注')

    is_suspicious = models.BooleanField(default=False, verbose_name='是否可疑')
    suspicious_reasons = models.JSONField(default=list, blank=True, verbose_name='可疑原因列表')

    hash_value = models.CharField(max_length=64, blank=True, default='', verbose_name='日志哈希')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']
        verbose_name = '审计日志'
        verbose_name_plural = '审计日志'
        indexes = [
            models.Index(fields=['category', 'action']),
            models.Index(fields=['created_at']),
            models.Index(fields=['operator_id']),
            models.Index(fields=['target_type', 'target_id']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['is_suspicious']),
            models.Index(fields=['status']),
        ]

    def __str__(self) -> str:
        return f'[{self.created_at}] {self.operator_username} - {self.get_category_display()} - {self.get_action_display()}'

    def save(self, *args, **kwargs):
        if not self.pk:
            self.hash_value = self._compute_hash()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError('审计日志不可删除')

    def _compute_hash(self) -> str:
        raw = json.dumps({
            'operator': self.operator_id,
            'category': self.category,
            'action': self.action,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'created_at': timezone.now().isoformat(),
            'ip': self.ip_address or '',
        }, sort_keys=True)
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        original_values = dict(zip(field_names, values))
        instance._original_values = original_values
        return instance

    def verify_integrity(self) -> bool:
        if not self.hash_value:
            return False
        current_hash = self._compute_hash()
        return current_hash == self.hash_value
