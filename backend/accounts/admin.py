from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'role', 'student_id', 'phone', 'security_question')
    search_fields = ('user__username', 'student_id', 'phone', 'security_question')
    list_filter = ('role',)
