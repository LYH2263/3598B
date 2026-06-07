from django.apps import AppConfig


class RefundInvoiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'refund_invoice'
    verbose_name = '退费与发票'
