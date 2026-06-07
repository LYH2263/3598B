from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/auth/', include('accounts.urls')),
    path('api/billing/', include('billing.urls')),
    path('api/notices/', include('notices.urls')),
    path('api/dormitory/', include('dormitory.urls')),
    path('api/activities/', include('activities.urls')),
    path('api/refund-invoice/', include('refund_invoice.urls')),
    path('api/config/', include('config_center.urls')),
    path('api/reminder/', include('reminder.urls')),
]
