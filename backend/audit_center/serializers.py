from rest_framework import serializers

from audit_center.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'operator',
            'operator_username',
            'operator_role',
            'category',
            'category_display',
            'action',
            'action_display',
            'status',
            'status_display',
            'target_type',
            'target_id',
            'target_display',
            'before_data',
            'after_data',
            'ip_address',
            'user_agent',
            'request_path',
            'request_method',
            'duration_ms',
            'error_message',
            'remark',
            'is_suspicious',
            'suspicious_reasons',
            'hash_value',
            'created_at',
        ]
        read_only_fields = fields


class AuditLogListQuerySerializer(serializers.Serializer):
    keyword = serializers.CharField(required=False, allow_blank=True, default='')
    category = serializers.CharField(required=False, allow_blank=True, default='')
    action = serializers.CharField(required=False, allow_blank=True, default='')
    status = serializers.CharField(required=False, allow_blank=True, default='')
    operator_id = serializers.IntegerField(required=False, default=None)
    operator_username = serializers.CharField(required=False, allow_blank=True, default='')
    target_type = serializers.CharField(required=False, allow_blank=True, default='')
    target_id = serializers.CharField(required=False, allow_blank=True, default='')
    ip_address = serializers.CharField(required=False, allow_blank=True, default='')
    is_suspicious = serializers.BooleanField(required=False, default=None)
    start_date = serializers.DateField(required=False, default=None)
    end_date = serializers.DateField(required=False, default=None)
    page = serializers.IntegerField(required=False, default=1, min_value=1)
    page_size = serializers.IntegerField(required=False, default=20, min_value=1, max_value=200)


class AuditTimelineQuerySerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=False, default=None)
    target_type = serializers.CharField(required=False, allow_blank=True, default='')
    target_id = serializers.CharField(required=False, allow_blank=True, default='')
    start_date = serializers.DateField(required=False, default=None)
    end_date = serializers.DateField(required=False, default=None)
    limit = serializers.IntegerField(required=False, default=100, min_value=1, max_value=500)


class AuditReportQuerySerializer(serializers.Serializer):
    period = serializers.ChoiceField(choices=['week', 'month'], required=False, default='week')
    start_date = serializers.DateField(required=False, default=None)
    end_date = serializers.DateField(required=False, default=None)


class AuditExportQuerySerializer(serializers.Serializer):
    keyword = serializers.CharField(required=False, allow_blank=True, default='')
    category = serializers.CharField(required=False, allow_blank=True, default='')
    action = serializers.CharField(required=False, allow_blank=True, default='')
    status = serializers.CharField(required=False, allow_blank=True, default='')
    operator_id = serializers.IntegerField(required=False, default=None)
    target_type = serializers.CharField(required=False, allow_blank=True, default='')
    target_id = serializers.CharField(required=False, allow_blank=True, default='')
    ip_address = serializers.CharField(required=False, allow_blank=True, default='')
    is_suspicious = serializers.BooleanField(required=False, default=None)
    start_date = serializers.DateField(required=False, default=None)
    end_date = serializers.DateField(required=False, default=None)
    format = serializers.ChoiceField(choices=['csv', 'json'], required=False, default='csv')


class AuditCategoryStatsSerializer(serializers.Serializer):
    category = serializers.CharField()
    category_display = serializers.CharField()
    count = serializers.IntegerField()
