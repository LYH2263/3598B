import logging
import time
from functools import wraps
from typing import Any, Callable, Optional

from django.contrib.auth.models import User
from django.db.models import Model
from django.http import HttpRequest
from django.utils import timezone

from audit_center.models import AuditLog
from audit_center.services.anomaly_service import AnomalyDetectionService

logger = logging.getLogger(__name__)


def _get_client_ip(request: HttpRequest) -> Optional[str]:
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def _get_user_role(user: Optional[User]) -> str:
    if not user or not user.is_authenticated:
        return ''
    profile = getattr(user, 'profile', None)
    return getattr(profile, 'role', '') if profile else ''


def _get_model_display_name(instance: Any) -> str:
    if hasattr(instance, '__str__'):
        try:
            return str(instance)[:255]
        except Exception:
            pass
    if hasattr(instance, 'name'):
        return str(instance.name)[:255]
    if hasattr(instance, 'username'):
        return str(instance.username)[:255]
    return ''


def _model_to_dict_safe(instance: Any, max_fields: int = 20) -> dict:
    data = {}
    if not hasattr(instance, '_meta'):
        return data
    try:
        fields = [f.name for f in instance._meta.get_fields() if not f.is_relation][:max_fields]
        for field_name in fields:
            try:
                value = getattr(instance, field_name)
                if isinstance(value, (str, int, float, bool, type(None))):
                    data[field_name] = value
                elif hasattr(value, 'isoformat'):
                    data[field_name] = value.isoformat()
                else:
                    data[field_name] = str(value)[:200]
            except Exception:
                continue
    except Exception:
        pass
    return data


class AuditService:
    @staticmethod
    def create_log(
        request: Optional[HttpRequest] = None,
        operator: Optional[User] = None,
        category: str = AuditLog.CATEGORY_OTHER,
        action: str = AuditLog.ACTION_OTHER,
        status: str = AuditLog.STATUS_SUCCESS,
        target: Optional[Any] = None,
        target_type: str = '',
        target_id: str = '',
        target_display: str = '',
        before_data: Optional[dict] = None,
        after_data: Optional[dict] = None,
        duration_ms: int = 0,
        error_message: str = '',
        remark: str = '',
    ) -> Optional[AuditLog]:
        try:
            operator_user = operator or (request.user if request and hasattr(request, 'user') else None)
            operator_username = operator_user.username if operator_user and operator_user.is_authenticated else ''
            operator_role = _get_user_role(operator_user)

            t_type = target_type
            t_id = target_id
            t_display = target_display

            if target is not None:
                if isinstance(target, Model):
                    t_type = t_type or f'{target._meta.app_label}.{target._meta.model_name}'
                    t_id = t_id or str(target.pk)
                    t_display = t_display or _get_model_display_name(target)
                else:
                    t_type = t_type or type(target).__name__
                    t_id = t_id or str(getattr(target, 'id', ''))
                    t_display = t_display or _get_model_display_name(target)

            if before_data is None and target is not None and isinstance(target, Model):
                before_data = _model_to_dict_safe(target)

            log = AuditLog(
                operator=operator_user if operator_user and operator_user.is_authenticated else None,
                operator_username=operator_username,
                operator_role=operator_role,
                category=category,
                action=action,
                status=status,
                target_type=t_type,
                target_id=t_id,
                target_display=t_display,
                before_data=before_data or {},
                after_data=after_data or {},
                ip_address=_get_client_ip(request) if request else None,
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:512] if request else '',
                request_path=request.path if request and hasattr(request, 'path') else '',
                request_method=request.method if request and hasattr(request, 'method') else '',
                duration_ms=duration_ms,
                error_message=error_message,
                remark=remark,
            )

            AnomalyDetectionService.assess(log)

            log.save()
            return log
        except Exception as e:
            logger.error('Failed to create audit log: %s', e, exc_info=True)
            return None

    @staticmethod
    def log_login_success(request: HttpRequest, user: User) -> Optional[AuditLog]:
        return AuditService.create_log(
            request=request,
            operator=user,
            category=AuditLog.CATEGORY_AUTH,
            action=AuditLog.ACTION_LOGIN_SUCCESS,
            target=user,
            remark='用户登录成功',
        )

    @staticmethod
    def log_login_failed(request: HttpRequest, username: str = '') -> Optional[AuditLog]:
        return AuditService.create_log(
            request=request,
            category=AuditLog.CATEGORY_AUTH,
            action=AuditLog.ACTION_LOGIN_FAILED,
            target_display=username or 'unknown',
            remark=f'登录失败: {username}',
        )

    @staticmethod
    def log_password_reset(request: HttpRequest, user: User) -> Optional[AuditLog]:
        return AuditService.create_log(
            request=request,
            operator=user,
            category=AuditLog.CATEGORY_AUTH,
            action=AuditLog.ACTION_PASSWORD_RESET,
            target=user,
            remark='密码重置成功',
        )

    @staticmethod
    def log_user_update(
        request: HttpRequest,
        target_user: User,
        before_data: dict,
        after_data: dict,
        operator: Optional[User] = None,
    ) -> Optional[AuditLog]:
        return AuditService.create_log(
            request=request,
            operator=operator or request.user,
            category=AuditLog.CATEGORY_USER,
            action=AuditLog.ACTION_UPDATE,
            target=target_user,
            before_data=before_data,
            after_data=after_data,
            remark='用户信息更新',
        )

    @staticmethod
    def log_role_change(
        request: HttpRequest,
        target_user: User,
        old_role: str,
        new_role: str,
    ) -> Optional[AuditLog]:
        return AuditService.create_log(
            request=request,
            category=AuditLog.CATEGORY_ROLE,
            action=AuditLog.ACTION_UPDATE,
            target=target_user,
            before_data={'role': old_role},
            after_data={'role': new_role},
            remark=f'角色变更: {old_role} -> {new_role}',
        )

    @staticmethod
    def log_wallet_freeze(
        request: HttpRequest,
        target_user: User,
        reason: str = '',
    ) -> Optional[AuditLog]:
        return AuditService.create_log(
            request=request,
            category=AuditLog.CATEGORY_WALLET,
            action=AuditLog.ACTION_FREEZE,
            target=target_user,
            after_data={'is_frozen': True, 'reason': reason},
            remark=f'钱包冻结: {reason}',
        )

    @staticmethod
    def log_wallet_unfreeze(
        request: HttpRequest,
        target_user: User,
        reason: str = '',
    ) -> Optional[AuditLog]:
        return AuditService.create_log(
            request=request,
            category=AuditLog.CATEGORY_WALLET,
            action=AuditLog.ACTION_UNFREEZE,
            target=target_user,
            after_data={'is_frozen': False, 'reason': reason},
            remark=f'钱包解冻: {reason}',
        )

    @staticmethod
    def log_order_review(
        request: HttpRequest,
        order: Any,
        action: str,
        remark: str = '',
    ) -> Optional[AuditLog]:
        audit_action = AuditLog.ACTION_APPROVE if action == 'approve' else AuditLog.ACTION_REJECT
        return AuditService.create_log(
            request=request,
            category=AuditLog.CATEGORY_ORDER,
            action=audit_action,
            target=order,
            after_data={'review_action': action, 'review_remark': remark},
            remark=f'订单审核: {action} {remark}',
        )

    @staticmethod
    def log_order_submit(
        request: HttpRequest,
        order: Any,
    ) -> Optional[AuditLog]:
        return AuditService.create_log(
            request=request,
            category=AuditLog.CATEGORY_ORDER,
            action=AuditLog.ACTION_SUBMIT,
            target=order,
            after_data={'order_no': getattr(order, 'order_no', ''), 'amount': str(getattr(order, 'amount', ''))},
            remark='订单提交',
        )

    @staticmethod
    def log_config_change(
        request: HttpRequest,
        config_key: str,
        old_value: Any,
        new_value: Any,
        group: str = '',
    ) -> Optional[AuditLog]:
        return AuditService.create_log(
            request=request,
            category=AuditLog.CATEGORY_CONFIG,
            action=AuditLog.ACTION_UPDATE,
            target_type=f'config.{group}' if group else 'config',
            target_id=config_key,
            target_display=f'{group}.{config_key}' if group else config_key,
            before_data={'value': str(old_value)},
            after_data={'value': str(new_value)},
            remark=f'配置变更: {config_key}',
        )

    @staticmethod
    def log_data_export(
        request: HttpRequest,
        data_type: str,
        count: int = 0,
    ) -> Optional[AuditLog]:
        return AuditService.create_log(
            request=request,
            category=AuditLog.CATEGORY_DATA,
            action=AuditLog.ACTION_EXPORT,
            target_type='data_export',
            target_id=data_type,
            target_display=f'{data_type} 数据导出',
            after_data={'data_type': data_type, 'count': count},
            remark=f'导出 {data_type} 数据 {count} 条',
        )

    @staticmethod
    def log_data_import(
        request: HttpRequest,
        data_type: str,
        success_count: int = 0,
        failed_count: int = 0,
    ) -> Optional[AuditLog]:
        return AuditService.create_log(
            request=request,
            category=AuditLog.CATEGORY_DATA,
            action=AuditLog.ACTION_IMPORT,
            target_type='data_import',
            target_id=data_type,
            target_display=f'{data_type} 数据导入',
            after_data={'data_type': data_type, 'success': success_count, 'failed': failed_count},
            remark=f'导入 {data_type} 数据，成功 {success_count} 条，失败 {failed_count} 条',
        )


def audit_log(
    category: str = AuditLog.CATEGORY_OTHER,
    action: str = AuditLog.ACTION_OTHER,
    target_from: str = '',
    target_param: str = '',
    capture_response: bool = False,
    remark: str = '',
):
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs) -> Any:
            start_time = time.time()
            error_msg = ''
            status = AuditLog.STATUS_SUCCESS
            result = None
            before_data = None
            after_data = None

            target_obj = None
            if target_param and target_param in kwargs:
                target_obj = kwargs[target_param]
            elif target_from:
                from django.apps import apps
                try:
                    app_label, model_name = target_from.rsplit('.', 1)
                    model_cls = apps.get_model(app_label, model_name)
                    pk = kwargs.get('pk') or kwargs.get('user_id') or kwargs.get('order_id')
                    if pk:
                        target_obj = model_cls.objects.filter(pk=pk).first()
                except Exception:
                    pass

            if target_obj is not None:
                before_data = _model_to_dict_safe(target_obj)

            try:
                result = view_func(request, *args, **kwargs)
            except Exception as e:
                status = AuditLog.STATUS_FAILED
                error_msg = str(e)[:1000]
                raise
            finally:
                duration_ms = int((time.time() - start_time) * 1000)

                if capture_response and result is not None:
                    try:
                        if hasattr(result, 'data'):
                            after_data = {'response': str(result.data)[:500]}
                    except Exception:
                        pass

                AuditService.create_log(
                    request=request,
                    category=category,
                    action=action,
                    status=status,
                    target=target_obj,
                    before_data=before_data,
                    after_data=after_data,
                    duration_ms=duration_ms,
                    error_message=error_msg,
                    remark=remark,
                )

            return result
        return wrapper
    return decorator
