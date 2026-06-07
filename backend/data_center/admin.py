from django.contrib import admin

from data_center.models import DataTask, ImportRowError


@admin.register(DataTask)
class DataTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'task_type', 'data_type', 'status', 'operator', 'progress_percent', 'created_at')
    list_filter = ('task_type', 'data_type', 'status')
    search_fields = ('operator__username', 'file_name')
    readonly_fields = ('created_at', 'updated_at', 'finished_at')


@admin.register(ImportRowError)
class ImportRowErrorAdmin(admin.ModelAdmin):
    list_display = ('id', 'task', 'row_number', 'is_corrected')
    list_filter = ('is_corrected',)
    search_fields = ('task__id',)
