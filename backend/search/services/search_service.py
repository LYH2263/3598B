from typing import Any

from django.contrib.auth.models import User
from django.db.models import Q

from accounts.models import Profile
from billing.models import ConsumptionRecord, RechargeOrder
from config_center.models import ConfigKey
from data_center.models import DataTask
from notices.models import Announcement


def _is_admin(user: User) -> bool:
    profile = getattr(user, 'profile', None)
    return bool(profile and profile.role == Profile.ROLE_ADMIN)


def _search_users(keyword: str, user: User, limit: int) -> list[dict[str, Any]]:
    qs = User.objects.select_related('profile').filter(
        Q(username__icontains=keyword)
        | Q(email__icontains=keyword)
        | Q(profile__student_id__icontains=keyword)
        | Q(profile__phone__icontains=keyword)
    )
    if not _is_admin(user):
        qs = qs.filter(id=user.id)
    qs = qs[:limit]

    results = []
    for u in qs:
        profile = getattr(u, 'profile', None)
        results.append({
            'id': u.id,
            'title': u.username,
            'subtitle': f"{profile.get_role_display() if profile else '用户'} | {u.email or '无邮箱'} | {profile.student_id or '' if profile else ''}",
            'extra': {
                'role': profile.role if profile else '',
                'student_id': profile.student_id if profile else '',
                'phone': profile.phone if profile else '',
                'email': u.email,
                'is_active': u.is_active,
            },
            'url': '/dashboard',
            'url_params': {'user_id': u.id, 'tab': 'users'},
        })
    return results


def _search_orders(keyword: str, user: User, limit: int) -> list[dict[str, Any]]:
    qs = RechargeOrder.objects.select_related('user').filter(
        Q(order_no__icontains=keyword)
        | Q(submit_remark__icontains=keyword)
        | Q(review_remark__icontains=keyword)
    )
    if not _is_admin(user):
        qs = qs.filter(user=user)
    qs = qs[:limit]

    results = []
    for o in qs:
        results.append({
            'id': o.id,
            'title': o.order_no,
            'subtitle': f"{o.get_status_display()} | ¥{o.amount} | {o.user.username} | {o.submit_remark or ''}",
            'extra': {
                'status': o.status,
                'amount': str(o.amount),
                'channel': o.channel,
                'user': o.user.username,
            },
            'url': '/dashboard',
            'url_params': {'order_id': o.id, 'tab': 'orders'},
        })
    return results


def _search_consumptions(keyword: str, user: User, limit: int) -> list[dict[str, Any]]:
    qs = ConsumptionRecord.objects.select_related('user').filter(
        Q(remark__icontains=keyword)
        | Q(operator__icontains=keyword)
    )
    if not _is_admin(user):
        qs = qs.filter(user=user)
    qs = qs[:limit]

    results = []
    for c in qs:
        results.append({
            'id': c.id,
            'title': f"{c.get_category_display()} ¥{c.cost_amount}",
            'subtitle': f"{c.user.username} | 用量{c.usage} | {c.remark or ''}",
            'extra': {
                'category': c.category,
                'cost_amount': str(c.cost_amount),
                'usage': str(c.usage),
                'user': c.user.username,
                'created_at': c.created_at.isoformat() if c.created_at else None,
            },
            'url': '/dashboard',
            'url_params': {'tab': 'consumption-admin' if _is_admin(user) else 'users'},
        })
    return results


def _search_announcements(keyword: str, user: User, limit: int) -> list[dict[str, Any]]:
    qs = Announcement.objects.filter(
        Q(title__icontains=keyword) | Q(content__icontains=keyword)
    )
    if not _is_admin(user):
        qs = qs.filter(is_active=True)
    qs = qs[:limit]

    results = []
    for a in qs:
        results.append({
            'id': a.id,
            'title': a.title,
            'subtitle': (a.content[:60] + '...') if len(a.content) > 60 else a.content,
            'extra': {
                'is_active': a.is_active,
                'published_at': a.published_at.isoformat() if a.published_at else None,
                'publisher': a.publisher.username if a.publisher else '',
            },
            'url': '/dashboard',
            'url_params': {'tab': 'announcements'},
        })
    return results


def _search_tasks(keyword: str, user: User, limit: int) -> list[dict[str, Any]]:
    qs = DataTask.objects.select_related('operator').filter(
        Q(file_name__icontains=keyword)
        | Q(error_message__icontains=keyword)
    )
    if not _is_admin(user):
        qs = qs.filter(operator=user)
    qs = qs[:limit]

    results = []
    for t in qs:
        results.append({
            'id': t.id,
            'title': f"{t.get_task_type_display()} - {t.get_data_type_display()}",
            'subtitle': f"{t.get_status_display()} | {t.file_name or '未命名'} | {t.operator.username}",
            'extra': {
                'task_type': t.task_type,
                'data_type': t.data_type,
                'status': t.status,
                'file_name': t.file_name,
                'progress_percent': t.progress_percent,
            },
            'url': '/data-center',
            'url_params': {'task_id': t.id},
        })
    return results


def _search_configs(keyword: str, user: User, limit: int) -> list[dict[str, Any]]:
    if not _is_admin(user):
        return []

    qs = ConfigKey.objects.filter(
        Q(key__icontains=keyword)
        | Q(group__icontains=keyword)
        | Q(description__icontains=keyword)
    )[:limit]

    results = []
    for c in qs:
        results.append({
            'id': c.id,
            'title': f"{c.group}.{c.key}",
            'subtitle': f"{c.get_value_type_display()} | {c.description or ''}",
            'extra': {
                'group': c.group,
                'key': c.key,
                'value_type': c.value_type,
                'is_editable': c.is_editable,
            },
            'url': '/config-center',
            'url_params': {'config_id': c.id},
        })
    return results


SEARCHERS = {
    'users': {'label': '用户', 'fn': _search_users, 'admin_only': False},
    'orders': {'label': '充值订单', 'fn': _search_orders, 'admin_only': False},
    'consumptions': {'label': '消费记录', 'fn': _search_consumptions, 'admin_only': False},
    'announcements': {'label': '公告', 'fn': _search_announcements, 'admin_only': False},
    'tasks': {'label': '数据任务(工单)', 'fn': _search_tasks, 'admin_only': False},
    'configs': {'label': '配置项', 'fn': _search_configs, 'admin_only': True},
}


def aggregate_search(
    keyword: str,
    user: User,
    limit: int = 5,
    categories: list[str] | None = None,
) -> dict[str, Any]:
    keyword = (keyword or '').strip()
    if not keyword:
        return {'keyword': '', 'groups': []}

    target_cats = categories if categories else list(SEARCHERS.keys())
    groups = []
    is_admin = _is_admin(user)

    for cat in target_cats:
        meta = SEARCHERS.get(cat)
        if not meta:
            continue
        if meta['admin_only'] and not is_admin:
            continue
        try:
            items = meta['fn'](keyword, user, limit)
        except Exception:
            items = []
        if items:
            groups.append({
                'category': cat,
                'label': meta['label'],
                'items': items,
                'has_more': len(items) >= limit,
            })

    return {
        'keyword': keyword,
        'groups': groups,
        'is_admin': is_admin,
    }
