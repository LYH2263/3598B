from django.apps import AppConfig


class AuditCenterConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'audit_center'
    verbose_name = '审计中台'
