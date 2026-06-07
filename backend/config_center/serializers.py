from rest_framework import serializers

from config_center.models import Campus, ConfigChangeLog, ConfigKey, ConfigValue


class CampusSerializer(serializers.ModelSerializer):
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Campus
        fields = (
            'id',
            'name',
            'code',
            'address',
            'description',
            'is_active',
            'created_at',
            'updated_at',
            'user_count',
        )
        read_only_fields = ('created_at', 'updated_at', 'user_count')

    def get_user_count(self, obj):
        return getattr(obj, 'user_count', obj.profiles.count())


class CampusSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campus
        fields = ('id', 'name', 'code', 'is_active')


class ConfigKeySerializer(serializers.ModelSerializer):
    value_type_label = serializers.CharField(source='get_value_type_display', read_only=True)

    class Meta:
        model = ConfigKey
        fields = (
            'id',
            'group',
            'key',
            'value_type',
            'value_type_label',
            'default_value',
            'min_value',
            'max_value',
            'regex_pattern',
            'options',
            'description',
            'is_editable',
            'sort_order',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')


class ConfigValueSerializer(serializers.ModelSerializer):
    campus_name = serializers.CharField(source='campus.name', default='全局', read_only=True)
    config_key_detail = ConfigKeySerializer(source='config_key', read_only=True)

    class Meta:
        model = ConfigValue
        fields = (
            'id',
            'config_key',
            'config_key_detail',
            'campus',
            'campus_name',
            'value',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')


class ConfigChangeLogSerializer(serializers.ModelSerializer):
    config_key_group = serializers.CharField(source='config_key.group', read_only=True)
    config_key_name = serializers.CharField(source='config_key.key', read_only=True)
    campus_name = serializers.SerializerMethodField()
    changed_by_username = serializers.SerializerMethodField()

    class Meta:
        model = ConfigChangeLog
        fields = (
            'id',
            'config_key',
            'config_key_group',
            'config_key_name',
            'campus',
            'campus_name',
            'old_value',
            'new_value',
            'changed_by',
            'changed_by_username',
            'changed_by_name',
            'changed_at',
            'remark',
        )

    def get_campus_name(self, obj):
        return obj.campus.name if obj.campus else '全局'

    def get_changed_by_username(self, obj):
        return obj.changed_by.username if obj.changed_by else obj.changed_by_name or 'system'


class ConfigUpdateSerializer(serializers.Serializer):
    value = serializers.CharField(allow_blank=True, required=True)
    campus_id = serializers.IntegerField(allow_null=True, required=False, default=None)
    remark = serializers.CharField(allow_blank=True, required=False, default='')


class ConfigItemDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    group = serializers.CharField()
    key = serializers.CharField()
    value_type = serializers.CharField()
    value_type_label = serializers.CharField()
    description = serializers.CharField()
    default_value = serializers.CharField()
    min_value = serializers.CharField(allow_null=True)
    max_value = serializers.CharField(allow_null=True)
    regex_pattern = serializers.CharField()
    options = serializers.ListField()
    is_editable = serializers.BooleanField()
    sort_order = serializers.IntegerField()
    global_value = serializers.CharField()
    campus_value = serializers.CharField()
    effective_value = serializers.CharField()
    effective_parsed = serializers.CharField(allow_null=True)
    has_campus_override = serializers.BooleanField()
