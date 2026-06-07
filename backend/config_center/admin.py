from django.contrib import admin

from config_center.models import Campus, ConfigChangeLog, ConfigKey, ConfigValue


@admin.register(Campus)
class CampusAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_active', 'created_at')
    search_fields = ('name', 'code', 'address')
    list_filter = ('is_active',)


@admin.register(ConfigKey)
class ConfigKeyAdmin(admin.ModelAdmin):
    list_display = ('group', 'key', 'value_type', 'default_value', 'is_editable', 'sort_order')
    search_fields = ('group', 'key', 'description')
    list_filter = ('group', 'value_type', 'is_editable')


@admin.register(ConfigValue)
class ConfigValueAdmin(admin.ModelAdmin):
    list_display = ('config_key', 'campus', 'value', 'updated_at')
    search_fields = ('config_key__group', 'config_key__key', 'value')
    list_filter = ('campus',)


@admin.register(ConfigChangeLog)
class ConfigChangeLogAdmin(admin.ModelAdmin):
    list_display = ('config_key', 'campus', 'old_value', 'new_value', 'changed_by_name', 'changed_at')
    search_fields = ('config_key__group', 'config_key__key', 'changed_by_name', 'remark')
    list_filter = ('campus', 'config_key__group')
    readonly_fields = ('changed_at',)
