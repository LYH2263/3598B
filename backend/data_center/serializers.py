from rest_framework import serializers

from data_center.models import DataTask, ImportRowError


class ImportRowErrorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportRowError
        fields = (
            'id', 'row_number', 'row_data', 'error_messages',
            'is_corrected', 'corrected_data', 'is_idempotent_skip', 'imported',
        )


class DataTaskSerializer(serializers.ModelSerializer):
    operator_name = serializers.CharField(source='operator.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    data_type_display = serializers.CharField(source='get_data_type_display', read_only=True)
    file_format_display = serializers.CharField(source='get_file_format_display', read_only=True)
    has_result = serializers.SerializerMethodField()
    has_error_file = serializers.SerializerMethodField()
    error_count = serializers.SerializerMethodField()

    class Meta:
        model = DataTask
        fields = (
            'id',
            'task_type', 'task_type_display',
            'data_type', 'data_type_display',
            'status', 'status_display',
            'progress_percent',
            'operator', 'operator_name',
            'file_name', 'file_hash',
            'file_format', 'file_format_display',
            'params',
            'total_rows', 'success_rows', 'skipped_rows', 'failed_rows',
            'error_message',
            'has_result', 'has_error_file', 'error_count',
            'parent_task',
            'created_at', 'updated_at', 'finished_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'finished_at', 'operator')

    def get_has_result(self, obj) -> bool:
        return bool(obj.result_file_path)

    def get_has_error_file(self, obj) -> bool:
        return bool(obj.error_file_path)

    def get_error_count(self, obj) -> int:
        return obj.row_errors.filter(is_idempotent_skip=False, imported=False).count()


class ImportUploadSerializer(serializers.Serializer):
    data_type = serializers.ChoiceField(choices=DataTask.DATA_TYPE_CHOICES)
    file_format = serializers.ChoiceField(
        choices=DataTask.FORMAT_CHOICES,
        required=False,
        default=DataTask.FORMAT_CSV,
    )


class ImportPreviewResultSerializer(serializers.Serializer):
    task_id = serializers.IntegerField()
    total_rows = serializers.IntegerField()
    error_count = serializers.IntegerField()
    warning_count = serializers.IntegerField()
    headers = serializers.ListField(child=serializers.CharField())
    field_labels = serializers.DictField()
    sample_data = serializers.ListField()
    all_rows = serializers.ListField(required=False)


class ImportSubmitSerializer(serializers.Serializer):
    task_id = serializers.IntegerField()
    corrected_rows = serializers.DictField(
        required=False,
        default=dict,
        help_text='修正后的行数据，key 为行号字符串',
    )


class ExportRequestSerializer(serializers.Serializer):
    data_type = serializers.ChoiceField(choices=DataTask.DATA_TYPE_CHOICES)
    file_format = serializers.ChoiceField(
        choices=DataTask.FORMAT_CHOICES,
        required=False,
        default=DataTask.FORMAT_CSV,
    )
    fields = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text='选择要导出的字段，空则导出全部',
    )
    filters = serializers.DictField(
        required=False,
        default=dict,
        help_text='筛选条件',
    )


class TaskRerunSerializer(serializers.Serializer):
    task_id = serializers.IntegerField()


class TaskListQuerySerializer(serializers.Serializer):
    task_type = serializers.ChoiceField(
        choices=[('', '全部')] + list(DataTask.TASK_TYPE_CHOICES),
        required=False,
        allow_blank=True,
        default='',
    )
    data_type = serializers.ChoiceField(
        choices=[('', '全部')] + list(DataTask.DATA_TYPE_CHOICES),
        required=False,
        allow_blank=True,
        default='',
    )
    status = serializers.ChoiceField(
        choices=[('', '全部')] + list(DataTask.STATUS_CHOICES),
        required=False,
        allow_blank=True,
        default='',
    )
    keyword = serializers.CharField(required=False, allow_blank=True, default='')
    page = serializers.IntegerField(required=False, default=1)
    page_size = serializers.IntegerField(required=False, default=20)
