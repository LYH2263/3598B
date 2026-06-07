from django.urls import path

from config_center.views import (
    CampusDetailAPIView,
    CampusListCreateAPIView,
    CampusSimpleListAPIView,
    ConfigChangeLogListAPIView,
    ConfigGroupListAPIView,
    ConfigInitAPIView,
    ConfigListByGroupAPIView,
    ConfigUpdateAPIView,
)

urlpatterns = [
    path('campuses/', CampusListCreateAPIView.as_view(), name='campus-list'),
    path('campuses/<int:pk>/', CampusDetailAPIView.as_view(), name='campus-detail'),
    path('campuses/simple/', CampusSimpleListAPIView.as_view(), name='campus-simple-list'),

    path('groups/', ConfigGroupListAPIView.as_view(), name='config-groups'),
    path('groups/<str:group>/', ConfigListByGroupAPIView.as_view(), name='config-list-by-group'),
    path('groups/<str:group>/keys/<str:key>/', ConfigUpdateAPIView.as_view(), name='config-update'),

    path('change-logs/', ConfigChangeLogListAPIView.as_view(), name='config-change-logs'),
    path('init/', ConfigInitAPIView.as_view(), name='config-init'),
]
