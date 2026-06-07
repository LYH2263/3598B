from django.contrib import admin

from reminder.models import Reminder, ReminderEvent, StudentReminderExemption


class ReminderEventInline(admin.TabularInline):
    model = ReminderEvent
    extra = 0
    readonly_fields = ('channel', 'sent_at', 'is_successful', 'error_message', 'notification_id')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'trigger_type',
        'status',
        'current_channel',
        'escalation_level',
        'title',
        'created_at',
        'last_escalated_at',
    )
    list_filter = ('trigger_type', 'status', 'current_channel', 'escalation_level', 'created_at')
    search_fields = ('user__username', 'title', 'content', 'trigger_key')
    readonly_fields = ('created_at', 'updated_at', 'handled_at', 'last_escalated_at')
    inlines = [ReminderEventInline]
    raw_id_fields = ('user', 'handled_by')


@admin.register(ReminderEvent)
class ReminderEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'reminder', 'channel', 'sent_at', 'is_successful')
    list_filter = ('channel', 'is_successful', 'sent_at')
    search_fields = ('reminder__user__username', 'error_message')
    readonly_fields = ('sent_at',)
    raw_id_fields = ('reminder',)


@admin.register(StudentReminderExemption)
class StudentReminderExemptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'is_exempted', 'exempted_at', 'reason', 'expires_at')
    list_filter = ('is_exempted', 'exempted_at')
    search_fields = ('user__username', 'reason')
    readonly_fields = ('created_at', 'updated_at', 'exempted_at')
    raw_id_fields = ('user', 'exempted_by')
