from django.urls import path

from audit_center.views import (
    AuditCategoryMetaAPIView,
    AuditExportAPIView,
    AuditLogDetailAPIView,
    AuditLogListAPIView,
    AuditOverviewAPIView,
    AuditReplayAPIView,
    AuditReportAPIView,
    AuditSuspiciousAPIView,
    AuditTimelineAPIView,
)

urlpatterns = [
    path('overview/', AuditOverviewAPIView.as_view(), name='audit-overview'),
    path('logs/', AuditLogListAPIView.as_view(), name='audit-log-list'),
    path('logs/<int:pk>/', AuditLogDetailAPIView.as_view(), name='audit-log-detail'),
    path('timeline/', AuditTimelineAPIView.as_view(), name='audit-timeline'),
    path('replay/', AuditReplayAPIView.as_view(), name='audit-replay'),
    path('report/', AuditReportAPIView.as_view(), name='audit-report'),
    path('suspicious/', AuditSuspiciousAPIView.as_view(), name='audit-suspicious'),
    path('meta/', AuditCategoryMetaAPIView.as_view(), name='audit-meta'),
    path('export/', AuditExportAPIView.as_view(), name='audit-export'),
]
