import json
import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from django.contrib.auth.models import User
from django.core.cache import cache

from config_center.models import Campus, ConfigChangeLog, ConfigKey, ConfigValue

logger = logging.getLogger(__name__)

CACHE_PREFIX = 'config_center:'
CACHE_TIMEOUT = 300


class ConfigService:
    @staticmethod
    def _cache_key(group: str, key: str, campus_id: int | None = None) -> str:
        scope = f'campus_{campus_id}' if campus_id else 'global'
        return f'{CACHE_PREFIX}{scope}:{group}.{key}'

    @staticmethod
    def _invalidate_cache(group: str, key: str):
        cache.delete(ConfigService._cache_key(group, key, None))
        for campus in Campus.objects.all():
            cache.delete(ConfigService._cache_key(group, key, campus.id))

    @staticmethod
    def _parse_value(value_type: str, raw_value: str) -> Any:
        if raw_value is None or raw_value == '':
            if value_type == ConfigKey.VALUE_TYPE_BOOLEAN:
                return False
            if value_type == ConfigKey.VALUE_TYPE_INTEGER:
                return 0
            if value_type == ConfigKey.VALUE_TYPE_DECIMAL:
                return Decimal('0')
            if value_type == ConfigKey.VALUE_TYPE_JSON:
                return None
            return ''

        if value_type == ConfigKey.VALUE_TYPE_STRING:
            return raw_value
        if value_type == ConfigKey.VALUE_TYPE_INTEGER:
            try:
                return int(raw_value)
            except (ValueError, TypeError):
                return 0
        if value_type == ConfigKey.VALUE_TYPE_DECIMAL:
            try:
                return Decimal(raw_value)
            except (InvalidOperation, TypeError):
                return Decimal('0')
        if value_type == ConfigKey.VALUE_TYPE_BOOLEAN:
            return str(raw_value).lower() in ('true', '1', 'yes', 'on')
        if value_type == ConfigKey.VALUE_TYPE_JSON:
            try:
                return json.loads(raw_value)
            except (json.JSONDecodeError, TypeError):
                return None
        return raw_value

    @staticmethod
    def _validate_value(config_key: ConfigKey, raw_value: str) -> tuple[bool, str]:
        if config_key.value_type == ConfigKey.VALUE_TYPE_INTEGER:
            try:
                val = int(raw_value) if raw_value else 0
            except ValueError:
                return False, '必须是整数。'
            if config_key.min_value is not None and val < int(config_key.min_value):
                return False, f'不能小于 {config_key.min_value}。'
            if config_key.max_value is not None and val > int(config_key.max_value):
                return False, f'不能大于 {config_key.max_value}。'
        elif config_key.value_type == ConfigKey.VALUE_TYPE_DECIMAL:
            try:
                val = Decimal(raw_value) if raw_value else Decimal('0')
            except InvalidOperation:
                return False, '必须是数字。'
            if config_key.min_value is not None and val < config_key.min_value:
                return False, f'不能小于 {config_key.min_value}。'
            if config_key.max_value is not None and val > config_key.max_value:
                return False, f'不能大于 {config_key.max_value}。'
        elif config_key.value_type == ConfigKey.VALUE_TYPE_STRING:
            if config_key.regex_pattern:
                if not re.match(config_key.regex_pattern, raw_value or ''):
                    return False, '格式不符合要求。'
            if config_key.options:
                opts = [str(o.get('value', o)) for o in config_key.options]
                if raw_value and raw_value not in opts:
                    return False, '必须是可选值之一。'
        elif config_key.value_type == ConfigKey.VALUE_TYPE_BOOLEAN:
            if raw_value and str(raw_value).lower() not in ('true', 'false', '1', '0', 'yes', 'no', 'on', 'off', ''):
                return False, '必须是布尔值。'
        elif config_key.value_type == ConfigKey.VALUE_TYPE_JSON:
            if raw_value:
                try:
                    json.loads(raw_value)
                except json.JSONDecodeError:
                    return False, '必须是合法的 JSON。'
        return True, ''

    @staticmethod
    def get_config_key(group: str, key: str) -> ConfigKey | None:
        return ConfigKey.objects.filter(group=group, key=key).first()

    @staticmethod
    def get_effective_raw_value(group: str, key: str, campus: Campus | int | None = None) -> str:
        campus_id = campus.id if isinstance(campus, Campus) else campus
        cache_key = ConfigService._cache_key(group, key, campus_id)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        config_key = ConfigService.get_config_key(group, key)
        if not config_key:
            return ''

        value_obj = None
        if campus_id:
            value_obj = ConfigValue.objects.filter(config_key=config_key, campus_id=campus_id).first()
        if value_obj is None:
            value_obj = ConfigValue.objects.filter(config_key=config_key, campus__isnull=True).first()

        raw_value = value_obj.value if value_obj else config_key.default_value
        cache.set(cache_key, raw_value, timeout=CACHE_TIMEOUT)
        return raw_value

    @staticmethod
    def get(group: str, key: str, campus: Campus | int | None = None) -> Any:
        config_key = ConfigService.get_config_key(group, key)
        if not config_key:
            return None
        raw_value = ConfigService.get_effective_raw_value(group, key, campus)
        return ConfigService._parse_value(config_key.value_type, raw_value)

    @staticmethod
    def get_for_user(group: str, key: str, user) -> Any:
        campus = None
        if user:
            profile = getattr(user, 'profile', None)
            if profile and profile.campus:
                campus = profile.campus
        return ConfigService.get(group, key, campus)

    @staticmethod
    def get_str(group: str, key: str, campus: Campus | int | None = None, default: str = '') -> str:
        val = ConfigService.get(group, key, campus)
        return str(val) if val is not None else default

    @staticmethod
    def get_int(group: str, key: str, campus: Campus | int | None = None, default: int = 0) -> int:
        val = ConfigService.get(group, key, campus)
        if isinstance(val, (int, float, Decimal)):
            return int(val)
        try:
            return int(val) if val else default
        except (ValueError, TypeError):
            return default

    @staticmethod
    def get_decimal(group: str, key: str, campus: Campus | int | None = None, default: Decimal | None = None) -> Decimal:
        val = ConfigService.get(group, key, campus)
        if isinstance(val, Decimal):
            return val
        if isinstance(val, (int, float)):
            return Decimal(str(val))
        try:
            return Decimal(str(val)) if val else (default or Decimal('0'))
        except (InvalidOperation, ValueError, TypeError):
            return default or Decimal('0')

    @staticmethod
    def get_bool(group: str, key: str, campus: Campus | int | None = None, default: bool = False) -> bool:
        val = ConfigService.get(group, key, campus)
        if isinstance(val, bool):
            return val
        return default

    @staticmethod
    def set_value(
        group: str,
        key: str,
        value: str,
        campus: Campus | int | None = None,
        changed_by: User | None = None,
        remark: str = '',
    ) -> tuple[ConfigValue | None, str]:
        config_key = ConfigService.get_config_key(group, key)
        if not config_key:
            return None, '配置项不存在。'
        if not config_key.is_editable:
            return None, '该配置项不可编辑。'

        ok, err = ConfigService._validate_value(config_key, value)
        if not ok:
            return None, err

        campus_id = campus.id if isinstance(campus, Campus) else campus
        campus_obj = campus if isinstance(campus, Campus) else (
            Campus.objects.filter(id=campus_id).first() if campus_id else None
        )

        value_obj, created = ConfigValue.objects.get_or_create(
            config_key=config_key,
            campus=campus_obj,
            defaults={'value': value},
        )

        old_value = value_obj.value
        if not created and old_value == value:
            return value_obj, ''

        value_obj.value = value
        value_obj.save()

        ConfigChangeLog.objects.create(
            config_key=config_key,
            campus=campus_obj,
            old_value=old_value,
            new_value=value,
            changed_by=changed_by,
            changed_by_name=changed_by.username if changed_by else '',
            remark=remark,
        )

        ConfigService._invalidate_cache(group, key)
        logger.info(
            'Config changed: [%s] %s.%s: %s -> %s by %s',
            campus_obj.name if campus_obj else '全局',
            group,
            key,
            old_value,
            value,
            changed_by.username if changed_by else 'system',
        )
        return value_obj, ''

    @staticmethod
    def list_groups() -> list[str]:
        return list(
            ConfigKey.objects.order_by('group').values_list('group', flat=True).distinct()
        )

    @staticmethod
    def list_configs_by_group(group: str, campus: Campus | int | None = None) -> list[dict]:
        campus_id = campus.id if isinstance(campus, Campus) else campus
        campus_obj = campus if isinstance(campus, Campus) else (
            Campus.objects.filter(id=campus_id).first() if campus_id else None
        )

        keys = ConfigKey.objects.filter(group=group).order_by('sort_order', 'key')
        result = []
        for ck in keys:
            global_val = ConfigValue.objects.filter(config_key=ck, campus__isnull=True).first()
            campus_val = None
            if campus_obj:
                campus_val = ConfigValue.objects.filter(config_key=ck, campus=campus_obj).first()

            effective_raw = campus_val.value if campus_val else (
                global_val.value if global_val else ck.default_value
            )

            result.append({
                'id': ck.id,
                'group': ck.group,
                'key': ck.key,
                'value_type': ck.value_type,
                'value_type_label': ck.get_value_type_display(),
                'description': ck.description,
                'default_value': ck.default_value,
                'min_value': str(ck.min_value) if ck.min_value is not None else None,
                'max_value': str(ck.max_value) if ck.max_value is not None else None,
                'regex_pattern': ck.regex_pattern,
                'options': ck.options,
                'is_editable': ck.is_editable,
                'sort_order': ck.sort_order,
                'global_value': global_val.value if global_val else '',
                'campus_value': campus_val.value if campus_val else '',
                'effective_value': effective_raw,
                'effective_parsed': ConfigService._parse_value(ck.value_type, effective_raw),
                'has_campus_override': campus_val is not None,
            })
        return result

    @staticmethod
    def get_change_logs(group: str | None = None, key: str | None = None, campus_id: int | None = None, limit: int = 100) -> list:
        qs = ConfigChangeLog.objects.select_related('config_key', 'campus', 'changed_by').all()
        if group:
            qs = qs.filter(config_key__group=group)
        if key:
            qs = qs.filter(config_key__key=key)
        if campus_id is not None:
            if campus_id == 0:
                qs = qs.filter(campus__isnull=True)
            else:
                qs = qs.filter(campus_id=campus_id)
        return list(qs[:limit])

    @staticmethod
    def ensure_default_configs():
        defaults = [
            {
                'group': 'pricing',
                'key': 'default_water_price',
                'value_type': ConfigKey.VALUE_TYPE_DECIMAL,
                'default_value': '3.50',
                'min_value': Decimal('0'),
                'max_value': Decimal('100'),
                'description': '默认水费单价（元/吨）',
                'sort_order': 1,
            },
            {
                'group': 'pricing',
                'key': 'default_electricity_price',
                'value_type': ConfigKey.VALUE_TYPE_DECIMAL,
                'default_value': '0.60',
                'min_value': Decimal('0'),
                'max_value': Decimal('100'),
                'description': '默认电费单价（元/度）',
                'sort_order': 2,
            },
            {
                'group': 'pricing',
                'key': 'late_fee_daily_rate',
                'value_type': ConfigKey.VALUE_TYPE_DECIMAL,
                'default_value': '0.0005',
                'min_value': Decimal('0'),
                'max_value': Decimal('1'),
                'description': '滞纳金日费率（如 0.0005 表示每日万分之五）',
                'sort_order': 3,
            },
            {
                'group': 'pricing',
                'key': 'late_fee_grace_days',
                'value_type': ConfigKey.VALUE_TYPE_INTEGER,
                'default_value': '0',
                'min_value': Decimal('0'),
                'max_value': Decimal('30'),
                'description': '滞纳金宽限天数（逾期后多少天开始计收）',
                'sort_order': 4,
            },
            {
                'group': 'pricing',
                'key': 'bill_default_due_days',
                'value_type': ConfigKey.VALUE_TYPE_INTEGER,
                'default_value': '15',
                'min_value': Decimal('1'),
                'max_value': Decimal('90'),
                'description': '账单默认缴费期限（天）',
                'sort_order': 5,
            },
            {
                'group': 'wallet',
                'key': 'auto_recharge_threshold',
                'value_type': ConfigKey.VALUE_TYPE_DECIMAL,
                'default_value': '20.00',
                'min_value': Decimal('0'),
                'max_value': Decimal('1000'),
                'description': '低额自动充值提醒阈值（元）',
                'sort_order': 1,
            },
            {
                'group': 'wallet',
                'key': 'auto_recharge_amount',
                'value_type': ConfigKey.VALUE_TYPE_DECIMAL,
                'default_value': '100.00',
                'min_value': Decimal('0'),
                'max_value': Decimal('10000'),
                'description': '自动充值默认金额（元）',
                'sort_order': 2,
            },
            {
                'group': 'security',
                'key': 'login_fail_lock_threshold',
                'value_type': ConfigKey.VALUE_TYPE_INTEGER,
                'default_value': '5',
                'min_value': Decimal('1'),
                'max_value': Decimal('50'),
                'description': '登录失败锁定阈值（次数）',
                'sort_order': 1,
            },
            {
                'group': 'security',
                'key': 'login_lock_duration_minutes',
                'value_type': ConfigKey.VALUE_TYPE_INTEGER,
                'default_value': '30',
                'min_value': Decimal('1'),
                'max_value': Decimal('1440'),
                'description': '登录失败锁定时长（分钟）',
                'sort_order': 2,
            },
            {
                'group': 'security',
                'key': 'captcha_expire_seconds',
                'value_type': ConfigKey.VALUE_TYPE_INTEGER,
                'default_value': '300',
                'min_value': Decimal('30'),
                'max_value': Decimal('3600'),
                'description': '图形验证码有效期（秒）',
                'sort_order': 3,
            },
            {
                'group': 'security',
                'key': 'email_code_ttl_seconds',
                'value_type': ConfigKey.VALUE_TYPE_INTEGER,
                'default_value': '300',
                'min_value': Decimal('30'),
                'max_value': Decimal('3600'),
                'description': '邮箱验证码有效期（秒）',
                'sort_order': 4,
            },
            {
                'group': 'notification',
                'key': 'silent_hour_start',
                'value_type': ConfigKey.VALUE_TYPE_INTEGER,
                'default_value': '22',
                'min_value': Decimal('0'),
                'max_value': Decimal('23'),
                'description': '通知静默时段开始（小时，24小时制）',
                'sort_order': 1,
            },
            {
                'group': 'notification',
                'key': 'silent_hour_end',
                'value_type': ConfigKey.VALUE_TYPE_INTEGER,
                'default_value': '8',
                'min_value': Decimal('0'),
                'max_value': Decimal('23'),
                'description': '通知静默时段结束（小时，24小时制）',
                'sort_order': 2,
            },
            {
                'group': 'notification',
                'key': 'enable_push_during_silent',
                'value_type': ConfigKey.VALUE_TYPE_BOOLEAN,
                'default_value': 'false',
                'description': '静默时段是否允许推送重要通知',
                'sort_order': 3,
            },
            {
                'group': 'reminder',
                'key': 'bill_due_soon_days',
                'value_type': ConfigKey.VALUE_TYPE_INTEGER,
                'default_value': '3',
                'min_value': Decimal('1'),
                'max_value': Decimal('30'),
                'description': '账单临近到期提醒天数（到期前多少天开始提醒）',
                'sort_order': 1,
            },
            {
                'group': 'reminder',
                'key': 'escalation_interval_days',
                'value_type': ConfigKey.VALUE_TYPE_INTEGER,
                'default_value': '3',
                'min_value': Decimal('1'),
                'max_value': Decimal('30'),
                'description': '催缴升级间隔天数（每多少天未处理升级到下一渠道）',
                'sort_order': 2,
            },
            {
                'group': 'reminder',
                'key': 'no_recharge_days_threshold',
                'value_type': ConfigKey.VALUE_TYPE_INTEGER,
                'default_value': '30',
                'min_value': Decimal('7'),
                'max_value': Decimal('180'),
                'description': '久未充值提醒阈值（连续多少天未充值触发提醒）',
                'sort_order': 3,
            },
            {
                'group': 'reminder',
                'key': 'predicted_consumption_daily',
                'value_type': ConfigKey.VALUE_TYPE_DECIMAL,
                'default_value': '5.00',
                'min_value': Decimal('0'),
                'max_value': Decimal('1000'),
                'description': '预估日均消费金额（元，用于预计欠费预测）',
                'sort_order': 4,
            },
            {
                'group': 'reminder',
                'key': 'enable_email_channel',
                'value_type': ConfigKey.VALUE_TYPE_BOOLEAN,
                'default_value': 'true',
                'description': '是否启用邮件通知渠道',
                'sort_order': 5,
            },
            {
                'group': 'reminder',
                'key': 'enable_parent_channel',
                'value_type': ConfigKey.VALUE_TYPE_BOOLEAN,
                'default_value': 'true',
                'description': '是否启用家长通知渠道',
                'sort_order': 6,
            },
            {
                'group': 'reminder',
                'key': 'enable_admin_ticket_channel',
                'value_type': ConfigKey.VALUE_TYPE_BOOLEAN,
                'default_value': 'true',
                'description': '是否启用管理员介入工单渠道',
                'sort_order': 7,
            },
        ]

        created_count = 0
        for item in defaults:
            _, created = ConfigKey.objects.get_or_create(
                group=item['group'],
                key=item['key'],
                defaults={
                    'value_type': item['value_type'],
                    'default_value': item['default_value'],
                    'min_value': item.get('min_value'),
                    'max_value': item.get('max_value'),
                    'description': item['description'],
                    'sort_order': item['sort_order'],
                },
            )
            if created:
                created_count += 1
        return created_count
