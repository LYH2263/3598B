from django.contrib import admin

from billing.models import (
    BalanceChangeLog,
    ConsumptionRecord,
    MeterReading,
    PriceStrategy,
    RechargeOrder,
    RechargeRecord,
    UtilityBill,
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


@admin.register(PriceStrategy)
class PriceStrategyAdmin(admin.ModelAdmin):
    list_display = ('id', 'category', 'strategy_type', 'unit_price', 'is_active', 'updated_at')
    search_fields = ('category',)
    list_filter = ('category', 'strategy_type', 'is_active')


@admin.register(MeterReading)
class MeterReadingAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'room',
        'category',
        'period_start',
        'period_end',
        'previous_reading',
        'current_reading',
        'usage',
        'source',
        'created_at',
    )
    search_fields = ('room__room_number', 'room__building__name', 'operator')
    list_filter = ('category', 'source')
    date_hierarchy = 'period_end'


@admin.register(UtilityBill)
class UtilityBillAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'bill_no',
        'user',
        'room',
        'category',
        'period_start',
        'period_end',
        'usage',
        'total_amount',
        'paid_amount',
        'status',
        'due_date',
        'paid_at',
    )
    search_fields = ('bill_no', 'user__username', 'room__room_number', 'room__building__name')
    list_filter = ('category', 'status')
    date_hierarchy = 'period_end'
    readonly_fields = ('bill_no',)
