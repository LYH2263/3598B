from django.utils import timezone
from rest_framework import serializers

from notices.models import Announcement, UserNotification


class AnnouncementSerializer(serializers.ModelSerializer):
    publisher_name = serializers.CharField(source='publisher.username', read_only=True)

    class Meta:
        model = Announcement
        fields = ('id', 'title', 'content', 'is_active', 'publisher_name', 'published_at')


class AnnouncementCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    content = serializers.CharField(max_length=4000)
    is_active = serializers.BooleanField(default=True)

    def create(self, validated_data):
        request = self.context['request']
        return Announcement.objects.create(
            title=validated_data['title'].strip(),
            content=validated_data['content'].strip(),
            is_active=validated_data.get('is_active', True),
            publisher=request.user,
        )


class UserNotificationSerializer(serializers.ModelSerializer):
    notice_type_display = serializers.CharField(source='get_notice_type_display', read_only=True)

    class Meta:
        model = UserNotification
        fields = (
            'id',
            'title',
            'content',
            'notice_type',
            'notice_type_display',
            'is_read',
            'created_at',
            'read_at',
        )


class NotificationReadSerializer(serializers.Serializer):
    notification_id = serializers.IntegerField(required=False)
    mark_all = serializers.BooleanField(default=False)

    def save(self, **kwargs):
        request = self.context['request']
        mark_all = self.validated_data.get('mark_all', False)
        notification_id = self.validated_data.get('notification_id')

        queryset = UserNotification.objects.filter(user=request.user, is_read=False)
        if mark_all:
            updated = queryset.update(is_read=True, read_at=timezone.now())
            return {'updated_count': updated}

        notification = queryset.filter(id=notification_id).first()
        if not notification:
            raise serializers.ValidationError({'notification_id': '通知不存在或已读。'})

        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=['is_read', 'read_at'])
        return {'updated_count': 1}
