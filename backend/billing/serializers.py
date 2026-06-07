from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework import serializers

from accounts.models import Profile
from billing.models import (
    BalanceChangeLog,
    ConsumptionRecord,
    DashboardPreference,
    MeterReading,
    PriceStrategy,
    RechargeOrder,
    RechargeRecord,
    SavedReport,
    UtilityBill,
    Wallet,
)
from billing.services.ledger_service import LedgerService
from billing.services.meter_service import MeterService
from billing.services.utility_bill_service import UtilityBillService


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ('balance', 'is_frozen', 'frozen_reason', 'frozen_at', 'updated_at')


class RechargeOrderSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.username', read_only=True)

    class Meta:
        model = RechargeOrder
        fields = (
            'id',
            'order_no',
            'user',
            'user_name',
            'amount',
            'channel',
            'status',
            'submit_remark',
            'review_remark',
            'reviewer_name',
            'reviewed_at',
            'created_at',
        )


class RechargeRecordSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = RechargeRecord
        fields = (
            'id',
            'user',
            'user_name',
            'amount',
            'channel',
            'operator',
            'remark',
            'created_at',
            'order',
        )
        read_only_fields = ('id', 'user_name', 'operator', 'created_at')


class ConsumptionRecordSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ConsumptionRecord
        fields = (
            'id',
            'user',
            'user_name',
            'category',
            'usage',
            'unit_price',
            'cost_amount',
            'meter_value',
            'operator',
            'remark',
            'created_at',
        )
        read_only_fields = ('id', 'user_name', 'cost_amount', 'operator', 'created_at')


class BalanceChangeLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = BalanceChangeLog
        fields = (
            'id',
            'user',
            'user_name',
            'change_type',
            'amount_delta',
            'balance_before',
            'balance_after',
            'related_order_no',
            'operator',
            'remark',
            'created_at',
        )


class RechargeCreateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=False)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    channel = serializers.ChoiceField(choices=RechargeRecord.CHANNEL_CHOICES)
    remark = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate(self, attrs):
        request = self.context['request']
        role = getattr(request.user.profile, 'role', Profile.ROLE_STUDENT)

        target_user = request.user
        if role == Profile.ROLE_ADMIN and attrs.get('user_id'):
            target_user = User.objects.filter(id=attrs['user_id']).first()
            if target_user is None:
                raise serializers.ValidationError({'user_id': '目标用户不存在。'})

        attrs['target_user'] = target_user
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        return LedgerService.create_recharge(
            user=validated_data['target_user'],
            amount=Decimal(validated_data['amount']),
            channel=validated_data['channel'],
            operator=request.user.username,
            remark=validated_data.get('remark', ''),
        )


class RechargeOrderCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    channel = serializers.ChoiceField(choices=RechargeOrder.CHANNEL_CHOICES)
    submit_remark = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def create(self, validated_data):
        request = self.context['request']
        return LedgerService.create_recharge_order(
            user=request.user,
            amount=Decimal(validated_data['amount']),
            channel=validated_data['channel'],
            submit_remark=validated_data.get('submit_remark', ''),
        )


class RechargeOrderReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=[
            (RechargeOrder.STATUS_APPROVED, '通过'),
            (RechargeOrder.STATUS_REJECTED, '驳回'),
        ]
    )
    review_remark = serializers.CharField(max_length=255, required=False, allow_blank=True)


class ConsumptionCreateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=False)
    category = serializers.ChoiceField(choices=ConsumptionRecord.CATEGORY_CHOICES)
    usage = serializers.DecimalField(max_digits=12, decimal_places=2)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    meter_value = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    remark = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate(self, attrs):
        request = self.context['request']
        role = getattr(request.user.profile, 'role', Profile.ROLE_STUDENT)

        target_user = request.user
        if role == Profile.ROLE_ADMIN and attrs.get('user_id'):
            target_user = User.objects.filter(id=attrs['user_id']).first()
            if target_user is None:
                raise serializers.ValidationError({'user_id': '目标用户不存在。'})

        attrs['target_user'] = target_user
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        meter_value = validated_data.get('meter_value')
        meter_decimal = Decimal(meter_value) if meter_value is not None else None

        return LedgerService.create_consumption(
            user=validated_data['target_user'],
            category=validated_data['category'],
            usage=Decimal(validated_data['usage']),
            unit_price=Decimal(validated_data['unit_price']),
            meter_value=meter_decimal,
            operator=request.user.username,
            remark=validated_data.get('remark', ''),
        )


class WalletActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=[('freeze', '冻结'), ('unfreeze', '解冻')])
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)


class PriceStrategySerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceStrategy
        fields = (
            'id',
            'category',
            'strategy_type',
            'unit_price',
            'tiers',
            'is_active',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class MeterReadingSerializer(serializers.ModelSerializer):
    room_name = serializers.CharField(source='room.__str__', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    building_id = serializers.IntegerField(source='room.building_id', read_only=True)

    class Meta:
        model = MeterReading
        fields = (
            'id',
            'room',
            'room_name',
            'building_id',
            'user',
            'user_name',
            'category',
            'period_start',
            'period_end',
            'previous_reading',
            'current_reading',
            'usage',
            'source',
            'operator',
            'remark',
            'created_at',
        )
        read_only_fields = ('id', 'room_name', 'building_id', 'user_name', 'usage', 'operator', 'created_at')


class MeterReadingCreateSerializer(serializers.Serializer):
    room_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=MeterReading.CATEGORY_CHOICES)
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    current_reading = serializers.DecimalField(max_digits=12, decimal_places=2)
    previous_reading = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    source = serializers.ChoiceField(
        choices=MeterReading.SOURCE_CHOICES,
        required=False,
        default=MeterReading.SOURCE_ADMIN,
    )
    remark = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def create(self, validated_data):
        request = self.context['request']
        previous = validated_data.get('previous_reading')
        return MeterService.create_reading(
            room_id=validated_data['room_id'],
            category=validated_data['category'],
            period_start=validated_data['period_start'],
            period_end=validated_data['period_end'],
            current_reading=Decimal(validated_data['current_reading']),
            previous_reading=Decimal(previous) if previous is not None else None,
            source=validated_data.get('source', MeterReading.SOURCE_ADMIN),
            operator=request.user.username,
            remark=validated_data.get('remark', ''),
        )


class UtilityBillSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    room_name = serializers.CharField(source='room.__str__', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    outstanding_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = UtilityBill
        fields = (
            'id',
            'bill_no',
            'user',
            'user_name',
            'room',
            'room_name',
            'category',
            'category_display',
            'period_start',
            'period_end',
            'previous_reading',
            'current_reading',
            'usage',
            'price_detail',
            'unit_price',
            'base_amount',
            'late_fee_amount',
            'total_amount',
            'paid_amount',
            'outstanding_amount',
            'due_date',
            'status',
            'status_display',
            'is_overdue',
            'meter_reading',
            'consumption_record',
            'parent_bill',
            'paid_at',
            'operator',
            'remark',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'bill_no',
            'user_name',
            'room_name',
            'status_display',
            'category_display',
            'outstanding_amount',
            'is_overdue',
            'created_at',
            'updated_at',
        )


class BillPaySerializer(serializers.Serializer):
    bill_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text='账单 ID 列表，单张缴纳可传单个 bill_id',
    )
    bill_id = serializers.IntegerField(required=False)

    def validate(self, attrs):
        bill_ids = attrs.get('bill_ids') or []
        if attrs.get('bill_id'):
            bill_ids = [attrs['bill_id']]
        if not bill_ids:
            raise serializers.ValidationError('请选择要缴纳的账单。')
        attrs['bill_ids'] = bill_ids
        return attrs


class BillVoidSerializer(serializers.Serializer):
    remark = serializers.CharField(max_length=255, required=False, allow_blank=True)


class BillMergeSerializer(serializers.Serializer):
    bill_ids = serializers.ListField(child=serializers.IntegerField())

    def validate_bill_ids(self, value):
        if len(value) < 2:
            raise serializers.ValidationError('至少需要选择 2 张账单进行合并。')
        return value


class BillRegenerateSerializer(serializers.Serializer):
    pass


class BillBatchGenerateSerializer(serializers.Serializer):
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    category = serializers.ChoiceField(
        choices=[('', '全部'), ('water', '水费'), ('electricity', '电费')],
        required=False,
        allow_blank=True,
    )

    def create(self, validated_data):
        request = self.context['request']
        category = validated_data.get('category') or None
        bills = UtilityBillService.generate_bills_for_period(
            period_start=validated_data['period_start'],
            period_end=validated_data['period_end'],
            category=category,
            operator=request.user.username,
        )
        return bills


class SavedReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedReport
        fields = (
            'id',
            'name',
            'description',
            'dataset',
            'dimensions',
            'measures',
            'filters',
            'chart_type',
            'chart_config',
            'is_pinned',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')


class DatasetQuerySerializer(serializers.Serializer):
    dataset = serializers.ChoiceField(
        choices=[
            ('recharge', '充值流水'),
            ('consumption', '消费流水'),
            ('user_growth', '用户增长'),
        ]
    )
    dimensions = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )
    measures = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )
    filters = serializers.DictField(required=False, default=dict)


class DashboardPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardPreference
        fields = ('layout', 'updated_at')
        read_only_fields = ('updated_at',)
