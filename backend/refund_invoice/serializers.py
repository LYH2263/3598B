from decimal import Decimal

from rest_framework import serializers

from billing.models import RechargeRecord
from refund_invoice.models import (
    InvoiceRequest,
    InvoiceRequestItem,
    InvoiceTitle,
    RefundRequest,
)
from refund_invoice.services.invoice_service import InvoiceService
from refund_invoice.services.refund_service import RefundService


class RefundRequestSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.username', read_only=True, default='')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    recharge_amount = serializers.DecimalField(
        source='recharge_record.amount',
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )
    recharge_created_at = serializers.DateTimeField(
        source='recharge_record.created_at',
        read_only=True,
    )

    class Meta:
        model = RefundRequest
        fields = (
            'id',
            'refund_no',
            'user',
            'user_name',
            'recharge_record',
            'recharge_amount',
            'recharge_created_at',
            'amount',
            'reason',
            'attachment_url',
            'status',
            'status_display',
            'reviewer_name',
            'review_remark',
            'reviewed_at',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'refund_no',
            'user',
            'user_name',
            'reviewer_name',
            'review_remark',
            'reviewed_at',
            'created_at',
            'updated_at',
        )


class RefundCreateSerializer(serializers.Serializer):
    recharge_record_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    reason = serializers.CharField(max_length=500)
    attachment_url = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def create(self, validated_data):
        request = self.context['request']
        return RefundService.create_refund_request(
            user=request.user,
            recharge_record_id=validated_data['recharge_record_id'],
            amount=Decimal(validated_data['amount']),
            reason=validated_data['reason'],
            attachment_url=validated_data.get('attachment_url', ''),
        )


class RefundReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=[
            (RefundRequest.STATUS_APPROVED, '通过'),
            (RefundRequest.STATUS_REJECTED, '拒绝'),
        ]
    )
    review_remark = serializers.CharField(max_length=500, required=False, allow_blank=True)


class RefundableRechargeSerializer(serializers.ModelSerializer):
    remaining_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = RechargeRecord
        fields = (
            'id',
            'amount',
            'channel',
            'operator',
            'remark',
            'created_at',
            'remaining_amount',
        )


class InvoiceTitleSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceTitle
        fields = (
            'id',
            'title_type',
            'title_name',
            'tax_no',
            'email',
            'is_default',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class InvoiceTitleCreateSerializer(serializers.Serializer):
    title_type = serializers.ChoiceField(choices=InvoiceTitle.TYPE_CHOICES)
    title_name = serializers.CharField(max_length=200)
    tax_no = serializers.CharField(max_length=50, required=False, allow_blank=True)
    email = serializers.EmailField(max_length=200)
    is_default = serializers.BooleanField(required=False, default=False)

    def create(self, validated_data):
        request = self.context['request']
        return InvoiceService.create_title(
            user=request.user,
            title_type=validated_data['title_type'],
            title_name=validated_data['title_name'],
            email=validated_data['email'],
            tax_no=validated_data.get('tax_no', ''),
            is_default=validated_data.get('is_default', False),
        )


class InvoiceTitleUpdateSerializer(serializers.Serializer):
    title_type = serializers.ChoiceField(choices=InvoiceTitle.TYPE_CHOICES, required=False)
    title_name = serializers.CharField(max_length=200, required=False)
    tax_no = serializers.CharField(max_length=50, required=False, allow_blank=True)
    email = serializers.EmailField(max_length=200, required=False)
    is_default = serializers.BooleanField(required=False)


class InvoiceRequestItemSerializer(serializers.ModelSerializer):
    recharge_amount = serializers.DecimalField(
        source='recharge_record.amount',
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )
    recharge_created_at = serializers.DateTimeField(
        source='recharge_record.created_at',
        read_only=True,
    )

    class Meta:
        model = InvoiceRequestItem
        fields = (
            'id',
            'recharge_record',
            'recharge_amount',
            'recharge_created_at',
            'amount',
            'created_at',
        )


class InvoiceRequestSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.username', read_only=True, default='')
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    title_info = InvoiceTitleSerializer(source='title', read_only=True)
    items = InvoiceRequestItemSerializer(many=True, read_only=True)

    class Meta:
        model = InvoiceRequest
        fields = (
            'id',
            'invoice_no',
            'user',
            'user_name',
            'title',
            'title_info',
            'total_amount',
            'remark',
            'status',
            'status_display',
            'invoice_number',
            'download_url',
            'reviewer_name',
            'review_remark',
            'reviewed_at',
            'items',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'invoice_no',
            'user',
            'user_name',
            'status_display',
            'title_info',
            'invoice_number',
            'download_url',
            'reviewer_name',
            'review_remark',
            'reviewed_at',
            'items',
            'created_at',
            'updated_at',
        )


class InvoiceItemInputSerializer(serializers.Serializer):
    recharge_record_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class InvoiceCreateSerializer(serializers.Serializer):
    title_id = serializers.IntegerField()
    items = InvoiceItemInputSerializer(many=True)
    remark = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('请选择至少一笔充值记录。')
        return value

    def create(self, validated_data):
        request = self.context['request']
        items = [
            {
                'recharge_record_id': item['recharge_record_id'],
                'amount': Decimal(item['amount']),
            }
            for item in validated_data['items']
        ]
        return InvoiceService.create_invoice_request(
            user=request.user,
            title_id=validated_data['title_id'],
            items=items,
            remark=validated_data.get('remark', ''),
        )


class InvoiceProcessSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=[
            (InvoiceRequest.STATUS_ISSUED, '开具'),
            (InvoiceRequest.STATUS_REJECTED, '驳回'),
        ]
    )
    invoice_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    download_url = serializers.CharField(max_length=500, required=False, allow_blank=True)
    review_remark = serializers.CharField(max_length=500, required=False, allow_blank=True)


class InvoiceVoidSerializer(serializers.Serializer):
    review_remark = serializers.CharField(max_length=500, required=False, allow_blank=True)


class InvoiceableRechargeSerializer(serializers.ModelSerializer):
    remaining_invoiceable = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = RechargeRecord
        fields = (
            'id',
            'amount',
            'channel',
            'operator',
            'remark',
            'created_at',
            'remaining_invoiceable',
        )
