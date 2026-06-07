from django.urls import path

from refund_invoice.views import (
    InvoiceableRechargesAPIView,
    InvoiceProcessAPIView,
    InvoiceRequestDetailAPIView,
    InvoiceRequestListCreateAPIView,
    InvoiceTitleDetailAPIView,
    InvoiceTitleListCreateAPIView,
    InvoiceTitleSetDefaultAPIView,
    InvoiceVoidAPIView,
    RefundCancelAPIView,
    RefundListCreateAPIView,
    RefundReviewAPIView,
    RefundableRechargesAPIView,
)

urlpatterns = [
    path('refunds/', RefundListCreateAPIView.as_view(), name='refunds'),
    path('refunds/<int:refund_id>/cancel/', RefundCancelAPIView.as_view(), name='refund-cancel'),
    path('refunds/<int:refund_id>/review/', RefundReviewAPIView.as_view(), name='refund-review'),
    path('refunds/refundable-recharges/', RefundableRechargesAPIView.as_view(), name='refundable-recharges'),

    path('invoice-titles/', InvoiceTitleListCreateAPIView.as_view(), name='invoice-titles'),
    path('invoice-titles/<int:title_id>/', InvoiceTitleDetailAPIView.as_view(), name='invoice-title-detail'),
    path('invoice-titles/<int:title_id>/set-default/', InvoiceTitleSetDefaultAPIView.as_view(), name='invoice-title-set-default'),

    path('invoices/', InvoiceRequestListCreateAPIView.as_view(), name='invoices'),
    path('invoices/<int:pk>/', InvoiceRequestDetailAPIView.as_view(), name='invoice-detail'),
    path('invoices/<int:pk>/process/', InvoiceProcessAPIView.as_view(), name='invoice-process'),
    path('invoices/<int:pk>/void/', InvoiceVoidAPIView.as_view(), name='invoice-void'),
    path('invoices/invoiceable-recharges/', InvoiceableRechargesAPIView.as_view(), name='invoiceable-recharges'),
]
