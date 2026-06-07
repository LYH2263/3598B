from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import UniqueConstraint


class Campus(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='校区名称')
    code = models.CharField(max_length=50, unique=True, verbose_name='校区编码')
    address = models.CharField(max_length=255, blank=True, default='', verbose_name='校区地址')
    description = models.CharField(max_length=500, blank=True, default='', verbose_name='备注说明')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'campuses'
        verbose_name = '校区'
        verbose_name_plural = '校区'
        ordering = ['code']

    def __str__(self) -> str:
        return f'{self.name}({self.code})'


class ConfigKey(models.Model):
    VALUE_TYPE_STRING = 'string'
    VALUE_TYPE_INTEGER = 'integer'
    VALUE_TYPE_DECIMAL = 'decimal'
    VALUE_TYPE_BOOLEAN = 'boolean'
    VALUE_TYPE_JSON = 'json'

    VALUE_TYPE_CHOICES = [
        (VALUE_TYPE_STRING, '字符串'),
        (VALUE_TYPE_INTEGER, '整数'),
        (VALUE_TYPE_DECIMAL, '小数'),
        (VALUE_TYPE_BOOLEAN, '布尔值'),
        (VALUE_TYPE_JSON, 'JSON对象'),
    ]

    group = models.CharField(max_length=100, verbose_name='配置分组')
    key = models.CharField(max_length=100, verbose_name='配置键')
    value_type = models.CharField(max_length=20, choices=VALUE_TYPE_CHOICES, default=VALUE_TYPE_STRING, verbose_name='值类型')
    default_value = models.TextField(blank=True, default='', verbose_name='全局默认值')
    min_value = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True, verbose_name='最小值(数值型)')
    max_value = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True, verbose_name='最大值(数值型)')
    regex_pattern = models.CharField(max_length=500, blank=True, default='', verbose_name='正则校验(字符串)')
    options = models.JSONField(default=list, blank=True, verbose_name='可选值列表')
    description = models.CharField(max_length=500, blank=True, default='', verbose_name='配置说明')
    is_editable = models.BooleanField(default=True, verbose_name='是否可编辑')
    sort_order = models.IntegerField(default=0, verbose_name='排序权重')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'config_keys'
        verbose_name = '配置项定义'
        verbose_name_plural = '配置项定义'
        constraints = [
            UniqueConstraint(fields=['group', 'key'], name='unique_config_group_key'),
        ]
        ordering = ['group', 'sort_order', 'key']

    def __str__(self) -> str:
        return f'{self.group}.{self.key}'

    def clean(self):
        super().clean()
        if self.min_value is not None and self.max_value is not None and self.min_value > self.max_value:
            raise ValidationError({'min_value': '最小值不能大于最大值。'})


class ConfigValue(models.Model):
    config_key = models.ForeignKey(ConfigKey, on_delete=models.CASCADE, related_name='values', verbose_name='配置项')
    campus = models.ForeignKey(Campus, on_delete=models.CASCADE, related_name='config_values', null=True, blank=True, verbose_name='校区(空为全局默认)')
    value = models.TextField(blank=True, default='', verbose_name='配置值')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'config_values'
        verbose_name = '配置值'
        verbose_name_plural = '配置值'
        constraints = [
            UniqueConstraint(fields=['config_key', 'campus'], name='unique_config_value_per_campus'),
        ]
        ordering = ['config_key__group', 'config_key__sort_order', 'campus__code']

    def __str__(self) -> str:
        campus_label = self.campus.name if self.campus else '全局'
        return f'{campus_label}: {self.config_key.group}.{self.config_key.key} = {self.value}'


class ConfigChangeLog(models.Model):
    config_key = models.ForeignKey(ConfigKey, on_delete=models.CASCADE, related_name='change_logs', verbose_name='配置项')
    campus = models.ForeignKey(Campus, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='校区')
    old_value = models.TextField(blank=True, default='', verbose_name='变更前值')
    new_value = models.TextField(blank=True, default='', verbose_name='变更后值')
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='config_changes', verbose_name='变更人')
    changed_by_name = models.CharField(max_length=150, blank=True, default='', verbose_name='变更人用户名(冗余)')
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name='变更时间')
    remark = models.CharField(max_length=500, blank=True, default='', verbose_name='变更备注')

    class Meta:
        db_table = 'config_change_logs'
        verbose_name = '配置变更日志'
        verbose_name_plural = '配置变更日志'
        ordering = ['-changed_at']

    def __str__(self) -> str:
        campus_label = self.campus.name if self.campus else '全局'
        return f'[{campus_label}] {self.config_key.group}.{self.config_key.key}: {self.old_value} -> {self.new_value}'
