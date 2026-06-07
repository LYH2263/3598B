from django.contrib import admin

from billing.models import (
    BalanceChangeLog,
    ConsumptionRecord,
    RechargeOrder,
    RechargeRecord,
    Wallet,
)


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'balance', 'is_frozen', 'updated_at')
    search_fields = ('user__username',)
    list_filter = ('is_frozen',)


@admin.register(RechargeOrder)
class RechargeOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'order_no', 'user', 'amount', 'channel', 'status', 'reviewer', 'created_at')
    search_fields = ('order_no', 'user__username')
    list_filter = ('status', 'channel')


@admin.register(RechargeRecord)
class RechargeRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'channel', 'operator', 'created_at')
    search_fields = ('user__username', 'operator', 'order__order_no')
    list_filter = ('channel',)


@admin.register(ConsumptionRecord)
class ConsumptionRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'category', 'usage', 'unit_price', 'cost_amount', 'created_at')
    search_fields = ('user__username', 'operator')
    list_filter = ('category',)


@admin.register(BalanceChangeLog)
class BalanceChangeLogAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'change_type',
        'amount_delta',
        'balance_before',
        'balance_after',
        'operator',
        'created_at',
    )
    search_fields = ('user__username', 'operator', 'related_order_no')
    list_filter = ('change_type',)
