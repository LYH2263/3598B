from django.contrib.auth.models import User
from django.db import models


class Announcement(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    publisher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='published_announcements')
    published_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'announcements'
        ordering = ['-published_at']


class UserNotification(models.Model):
    TYPE_ANNOUNCEMENT = 'announcement'
    TYPE_ORDER = 'order'
    TYPE_SECURITY = 'security'
    TYPE_SYSTEM = 'system'

    TYPE_CHOICES = [
        (TYPE_ANNOUNCEMENT, '系统公告'),
        (TYPE_ORDER, '订单通知'),
        (TYPE_SECURITY, '安全通知'),
        (TYPE_SYSTEM, '系统消息'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    content = models.TextField()
    notice_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_SYSTEM)
    is_read = models.BooleanField(default=False)
    related_announcement = models.ForeignKey(
        Announcement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'user_notifications'
        ordering = ['-created_at']
