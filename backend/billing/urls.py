from django.urls import path

from billing.views import (
    ConsumptionListCreateAPIView,
    ConsumptionStatsAPIView,
    DashboardAPIView,
    RechargeListCreateAPIView,
    RechargeOrderListCreateAPIView,
    RechargeOrderReviewAPIView,
    WalletActionAPIView,
    WalletLogListAPIView,
)

urlpatterns = [
    path('dashboard/', DashboardAPIView.as_view(), name='dashboard'),
    path('recharges/', RechargeListCreateAPIView.as_view(), name='recharges'),
    path('recharge-orders/', RechargeOrderListCreateAPIView.as_view(), name='recharge-orders'),
    path('recharge-orders/<int:order_id>/review/', RechargeOrderReviewAPIView.as_view(), name='recharge-order-review'),
    path('consumptions/', ConsumptionListCreateAPIView.as_view(), name='consumptions'),
    path('consumptions/stats/', ConsumptionStatsAPIView.as_view(), name='consumptions-stats'),
    path('wallets/<int:user_id>/action/', WalletActionAPIView.as_view(), name='wallet-action'),
    path('wallet-logs/', WalletLogListAPIView.as_view(), name='wallet-logs'),
]
