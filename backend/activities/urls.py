from django.urls import path

from activities import views

urlpatterns = [
    path('activities/', views.ActivityListCreateAPIView.as_view(), name='activity-list-create'),
    path('activities/<int:pk>/', views.ActivityDetailAPIView.as_view(), name='activity-detail'),
    path('activities/<int:pk>/publish/', views.ActivityPublishAPIView.as_view(), name='activity-publish'),
    path(
        'activities/<int:pk>/generate-check-in-code/',
        views.ActivityGenerateCheckInCodeAPIView.as_view(),
        name='activity-generate-check-in-code',
    ),
    path('activities/<int:pk>/register/', views.ActivityRegisterAPIView.as_view(), name='activity-register'),
    path('activities/<int:pk>/check-in/', views.ActivityCheckInAPIView.as_view(), name='activity-check-in'),
    path('activities/<int:pk>/reviews/', views.ActivityReviewListCreateAPIView.as_view(), name='activity-reviews'),
    path('registrations/', views.ActivityRegistrationListAPIView.as_view(), name='activity-registrations'),
    path('registrations/my/', views.ActivityMyRegistrationsAPIView.as_view(), name='activity-my-registrations'),
    path(
        'registrations/<int:pk>/review/',
        views.ActivityRegistrationReviewAPIView.as_view(),
        name='activity-registration-review',
    ),
    path(
        'registrations/batch-review/',
        views.ActivityRegistrationBatchReviewAPIView.as_view(),
        name='activity-registration-batch-review',
    ),
    path('calendar/', views.ActivityCalendarAPIView.as_view(), name='activity-calendar'),
]
