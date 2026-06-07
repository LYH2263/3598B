from django.contrib import admin

from audit_center.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'created_at', 'operator_username', 'operator_role',
        'category', 'action', 'status', 'target_type', 'target_id',
        'ip_address', 'is_suspicious', 'duration_ms',
    ]
    list_filter = [
        'category', 'action', 'status', 'is_suspicious',
        'operator_role', 'created_at',
    ]
    search_fields = [
        'operator_username', 'target_type', 'target_id', 'target_display',
        'ip_address', 'remark',
    ]
    readonly_fields = [f.name for f in AuditLog._meta.get_fields()]
    ordering = ['-created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
