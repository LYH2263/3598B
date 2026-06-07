from django.contrib import admin

from notices.models import Announcement, UserNotification


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'is_active', 'publisher', 'published_at')
    search_fields = ('title', 'content')
    list_filter = ('is_active',)


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'notice_type', 'title', 'is_read', 'created_at')
    search_fields = ('user__username', 'title', 'content')
    list_filter = ('notice_type', 'is_read')
