from django.urls import path

from reminder.views import (
    AdminExemptionListAPIView,
    AdminReminderListAPIView,
    AdminReminderScanAPIView,
    AdminReminderStatsAPIView,
    AdminResumeRemindersAPIView,
    AdminStopAllRemindersAPIView,
    AdminTriggerReminderAPIView,
    StudentReminderHandleAPIView,
    StudentReminderListAPIView,
)

urlpatterns = [
    path('my/', StudentReminderListAPIView.as_view(), name='student-reminders'),
    path('my/handle/', StudentReminderHandleAPIView.as_view(), name='student-reminder-handle'),
    path('admin/list/', AdminReminderListAPIView.as_view(), name='admin-reminder-list'),
    path('admin/stats/', AdminReminderStatsAPIView.as_view(), name='admin-reminder-stats'),
    path('admin/trigger/', AdminTriggerReminderAPIView.as_view(), name='admin-reminder-trigger'),
    path('admin/stop-all/', AdminStopAllRemindersAPIView.as_view(), name='admin-reminder-stop-all'),
    path('admin/resume/', AdminResumeRemindersAPIView.as_view(), name='admin-reminder-resume'),
    path('admin/scan/', AdminReminderScanAPIView.as_view(), name='admin-reminder-scan'),
    path('admin/exemptions/', AdminExemptionListAPIView.as_view(), name='admin-exemption-list'),
]
