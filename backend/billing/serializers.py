from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework import serializers

from accounts.models import Profile
from billing.models import (
    BalanceChangeLog,
    ConsumptionRecord,
    RechargeOrder,
    RechargeRecord,
    Wallet,
)
from billing.services.ledger_service import LedgerService


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
