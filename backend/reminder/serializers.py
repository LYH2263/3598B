from django.contrib.auth.models import User
from rest_framework import serializers

from reminder.models import Reminder, ReminderEvent, StudentReminderExemption


class ReminderEventSerializer(serializers.ModelSerializer):
    channel_display = serializers.CharField(source='get_channel_display', read_only=True)

    class Meta:
        model = ReminderEvent
        fields = (
            'id',
            'channel',
            'channel_display',
            'sent_at',
            'is_successful',
            'error_message',
            'notification_id',
        )


class ReminderSerializer(serializers.ModelSerializer):
    trigger_type_display = serializers.CharField(source='get_trigger_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    current_channel_display = serializers.CharField(source='get_current_channel_display', read_only=True)
    handled_by_name = serializers.CharField(source='handled_by.username', read_only=True, default='')
    events = ReminderEventSerializer(many=True, read_only=True)

    class Meta:
        model = Reminder
        fields = (
            'id',
            'trigger_type',
            'trigger_type_display',
            'status',
            'status_display',
            'current_channel',
            'current_channel_display',
            'escalation_level',
            'last_escalated_at',
            'title',
            'content',
            'related_bill_id',
            'threshold_snapshot',
            'handled_at',
            'handled_by_name',
            'handled_note',
            'events',
            'created_at',
            'updated_at',
        )


class ReminderHandleSerializer(serializers.Serializer):
    reminder_id = serializers.IntegerField()
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')

    def save(self, **kwargs):
        from reminder.services import ReminderService

        request = self.context['request']
        reminder_id = self.validated_data['reminder_id']
        note = self.validated_data.get('note', '')

        reminder = Reminder.objects.filter(
            id=reminder_id,
            user=request.user,
            status=Reminder.STATUS_PENDING,
        ).first()
        if not reminder:
            raise serializers.ValidationError({'reminder_id': '提醒不存在或已处理。'})

        return ReminderService.mark_handled(reminder, handled_by=request.user, note=note)


class AdminReminderListQuerySerializer(serializers.Serializer):
    status = serializers.CharField(max_length=20, required=False)
    trigger_type = serializers.CharField(max_length=40, required=False)
    user_id = serializers.IntegerField(required=False)
    keyword = serializers.CharField(max_length=100, required=False)


class AdminTriggerReminderSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    trigger_type = serializers.ChoiceField(choices=Reminder.TRIGGER_CHOICES)
    title = serializers.CharField(max_length=200)
    content = serializers.CharField(max_length=2000)
    related_bill_id = serializers.IntegerField(required=False, allow_null=True, default=None)

    def validate_user_id(self, value):
        if not User.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError('用户不存在或未激活。')
        return value

    def save(self, **kwargs):
        from reminder.services import ReminderService

        request = self.context['request']
        user = User.objects.get(id=self.validated_data['user_id'])
        return ReminderService.trigger_manual_reminder(
            user=user,
            trigger_type=self.validated_data['trigger_type'],
            title=self.validated_data['title'],
            content=self.validated_data['content'],
            triggered_by=request.user,
            related_bill_id=self.validated_data.get('related_bill_id'),
        )


class AdminStopAllRemindersSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')

    def validate_user_id(self, value):
        if not User.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError('用户不存在或未激活。')
        return value

    def save(self, **kwargs):
        from reminder.services import ReminderService

        request = self.context['request']
        user = User.objects.get(id=self.validated_data['user_id'])
        return ReminderService.stop_all_for_user(
            user=user,
            stopped_by=request.user,
            reason=self.validated_data.get('reason', ''),
        )


class AdminResumeRemindersSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()

    def validate_user_id(self, value):
        if not User.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError('用户不存在或未激活。')
        return value

    def save(self, **kwargs):
        from reminder.services import ReminderService

        request = self.context['request']
        user = User.objects.get(id=self.validated_data['user_id'])
        return ReminderService.resume_for_user(user=user, resumed_by=request.user)


class StudentReminderExemptionSerializer(serializers.ModelSerializer):
    exempted_by_name = serializers.CharField(source='exempted_by.username', read_only=True, default='')
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = StudentReminderExemption
        fields = (
            'id',
            'username',
            'is_exempted',
            'exempted_by_name',
            'exempted_at',
            'reason',
            'expires_at',
            'created_at',
            'updated_at',
        )


class ReminderStatsSerializer(serializers.Serializer):
    total_pending = serializers.IntegerField()
    total_handled = serializers.IntegerField()
    total_stopped = serializers.IntegerField()
    total_resolved_auto = serializers.IntegerField()
    by_trigger_type = serializers.DictField()
    by_channel = serializers.DictField()
    exempted_count = serializers.IntegerField()
