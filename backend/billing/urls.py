from django.urls import path

from billing.views import (
    BillBatchGenerateAPIView,
    BillGenerateFromReadingAPIView,
    BillMergeAPIView,
    BillPayAPIView,
    BillRegenerateAPIView,
    BillVoidAPIView,
    ConsumptionListCreateAPIView,
    ConsumptionStatsAPIView,
    DashboardAPIView,
    LateFeeRunAPIView,
    MeterReadingListCreateAPIView,
    PriceStrategyDetailAPIView,
    PriceStrategyListCreateAPIView,
    RechargeListCreateAPIView,
    RechargeOrderListCreateAPIView,
    RechargeOrderReviewAPIView,
    UtilityBillDetailAPIView,
    UtilityBillListAPIView,
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

    path('price-strategies/', PriceStrategyListCreateAPIView.as_view(), name='price-strategies'),
    path('price-strategies/<int:pk>/', PriceStrategyDetailAPIView.as_view(), name='price-strategy-detail'),

    path('meter-readings/', MeterReadingListCreateAPIView.as_view(), name='meter-readings'),
    path('meter-readings/<int:reading_id>/generate-bills/', BillGenerateFromReadingAPIView.as_view(), name='generate-bills-from-reading'),

    path('bills/', UtilityBillListAPIView.as_view(), name='bills'),
    path('bills/<int:pk>/', UtilityBillDetailAPIView.as_view(), name='bill-detail'),
    path('bills/pay/', BillPayAPIView.as_view(), name='bill-pay'),
    path('bills/<int:pk>/void/', BillVoidAPIView.as_view(), name='bill-void'),
    path('bills/merge/', BillMergeAPIView.as_view(), name='bill-merge'),
    path('bills/<int:pk>/regenerate/', BillRegenerateAPIView.as_view(), name='bill-regenerate'),
    path('bills/batch-generate/', BillBatchGenerateAPIView.as_view(), name='bill-batch-generate'),
    path('bills/run-late-fees/', LateFeeRunAPIView.as_view(), name='bill-run-late-fees'),
]
