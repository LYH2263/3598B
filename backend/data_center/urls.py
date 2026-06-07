from django.urls import path

from data_center.views import (
    DataTypesMetaAPIView,
    ExportSubmitAPIView,
    ImportRowErrorsAPIView,
    ImportSubmitAPIView,
    ImportUploadAPIView,
    TaskDetailAPIView,
    TaskErrorDownloadAPIView,
    TaskListAPIView,
    TaskResultDownloadAPIView,
    TaskRerunAPIView,
    TaskStatsAPIView,
    TemplateDownloadAPIView,
)

urlpatterns = [
    path('data-types/', DataTypesMetaAPIView.as_view(), name='dc-data-types'),
    path('tasks/', TaskListAPIView.as_view(), name='dc-task-list'),
    path('tasks/stats/', TaskStatsAPIView.as_view(), name='dc-task-stats'),
    path('tasks/<int:task_id>/', TaskDetailAPIView.as_view(), name='dc-task-detail'),
    path('tasks/<int:task_id>/download/', TaskResultDownloadAPIView.as_view(), name='dc-task-download'),
    path('tasks/<int:task_id>/errors/download/', TaskErrorDownloadAPIView.as_view(), name='dc-task-error-download'),
    path('tasks/<int:task_id>/errors/', ImportRowErrorsAPIView.as_view(), name='dc-task-errors'),
    path('tasks/rerun/', TaskRerunAPIView.as_view(), name='dc-task-rerun'),
    path('templates/<str:data_type>/', TemplateDownloadAPIView.as_view(), name='dc-template-download'),
    path('import/upload/', ImportUploadAPIView.as_view(), name='dc-import-upload'),
    path('import/submit/', ImportSubmitAPIView.as_view(), name='dc-import-submit'),
    path('export/submit/', ExportSubmitAPIView.as_view(), name='dc-export-submit'),
]
