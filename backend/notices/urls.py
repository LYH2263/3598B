from django.urls import path

from notices.views import AnnouncementListCreateAPIView, NotificationListAPIView, NotificationReadAPIView

urlpatterns = [
    path('announcements/', AnnouncementListCreateAPIView.as_view(), name='announcements'),
    path('notifications/', NotificationListAPIView.as_view(), name='notifications'),
    path('notifications/read/', NotificationReadAPIView.as_view(), name='notifications-read'),
]
