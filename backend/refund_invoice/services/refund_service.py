from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from billing.models import BalanceChangeLog, RechargeRecord, Wallet
from notices.services import NotificationService
from refund_invoice.models import RefundRequest


class RefundService:
    @staticmethod
    def _money(value: Decimal) -> Decimal:
        return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @staticmethod
    def _next_refund_no() -> str:
        return f'RF{timezone.now().strftime("%Y%m%d%H%M%S")}{uuid4().hex[:6].upper()}'

    @staticmethod
    def _get_refunded_amount(recharge_record: RechargeRecord, exclude_id: int | None = None) -> Decimal:
        qs = RefundRequest.objects.filter(
            recharge_record=recharge_record,
            status__in=[RefundRequest.STATUS_PENDING, RefundRequest.STATUS_APPROVED],
        )
        if exclude_id:
            qs = qs.exclude(pk=exclude_id)
        total = qs.aggregate(total=__import__('django.db.models', fromlist=['Sum']).Sum('amount')).get('total')
        return RefundService._money(total or 0)

    @staticmethod
    @transaction.atomic
    def create_refund_request(
        user,
        recharge_record_id: int,
        amount: Decimal,
        reason: str,
        attachment_url: str = '',
    ) -> RefundRequest:
        amount = RefundService._money(amount)
        if amount <= 0:
            raise ValidationError('退费金额必须大于 0。')

        recharge_record = (
            RechargeRecord.objects.select_for_update()
            .select_related('user')
            .filter(id=recharge_record_id, user=user)
            .first()
        )
        if not recharge_record:
            raise ValidationError('充值记录不存在或不属于您。')

        refunded = RefundService._get_refunded_amount(recharge_record)
        remaining = RefundService._money(recharge_record.amount - refunded)
        if amount > remaining:
            raise ValidationError(f'该充值剩余可退金额为 ¥{remaining}。')

        wallet, _ = Wallet.objects.get_or_create(user=user)
        if wallet.is_frozen:
            raise ValidationError('账户已冻结，无法申请退费。')
        if wallet.balance < amount:
            raise ValidationError('钱包余额不足，无法申请该金额的退费。')

        request = RefundRequest.objects.create(
            refund_no=RefundService._next_refund_no(),
            user=user,
            recharge_record=recharge_record,
            amount=amount,
            reason=reason,
            attachment_url=attachment_url,
        )
        return request

    @staticmethod
    @transaction.atomic
    def cancel_refund_request(user, refund_id: int) -> RefundRequest:
        refund = (
            RefundRequest.objects.select_for_update()
            .select_related('user')
            .filter(id=refund_id, user=user)
            .first()
        )
        if not refund:
            raise ValidationError('退费申请不存在。')
        if refund.status != RefundRequest.STATUS_PENDING:
            raise ValidationError('只有待审核的申请可以撤销。')

        refund.status = RefundRequest.STATUS_CANCELLED
        refund.updated_at = timezone.now()
        refund.save(update_fields=['status', 'updated_at'])
        return refund

    @staticmethod
    @transaction.atomic
    def review_refund(
        refund: RefundRequest,
        action: str,
        reviewer,
        review_remark: str = '',
    ) -> RefundRequest:
        refund = (
            RefundRequest.objects.select_for_update()
            .select_related('user', 'recharge_record')
            .filter(id=refund.id)
            .first()
        )
        if not refund:
            raise ValidationError('退费申请不存在。')
        if refund.status != RefundRequest.STATUS_PENDING:
            raise ValidationError('该退费申请已处理，请勿重复审核。')

        if action not in {RefundRequest.STATUS_APPROVED, RefundRequest.STATUS_REJECTED}:
            raise ValidationError('非法审核动作。')

        if action == RefundRequest.STATUS_APPROVED:
            wallet = Wallet.objects.select_for_update().get(user=refund.user)
            if wallet.is_frozen:
                raise ValidationError('用户账户已冻结，无法完成退费。')
            if wallet.balance < refund.amount:
                raise ValidationError('用户钱包余额不足，无法完成退费扣减。')

            balance_before = wallet.balance
            wallet.balance = RefundService._money(wallet.balance - refund.amount)
            wallet.save(update_fields=['balance', 'updated_at'])

            BalanceChangeLog.objects.create(
                user=refund.user,
                wallet=wallet,
                change_type=BalanceChangeLog.TYPE_REFUND,
                amount_delta=RefundService._money(-refund.amount),
                balance_before=RefundService._money(balance_before),
                balance_after=RefundService._money(wallet.balance),
                related_order_no=refund.refund_no,
                operator=reviewer.username,
                remark=f'退费审核通过：{refund.reason}',
            )
            notify_title = '退费申请已通过'
            notify_content = f'退费申请 {refund.refund_no} 已审核通过，¥{refund.amount} 已从钱包扣除。'
        else:
            notify_title = '退费申请被拒绝'
            notify_content = f'退费申请 {refund.refund_no} 已被拒绝。'
            if review_remark:
                notify_content += f'原因：{review_remark}'

        refund.status = action
        refund.reviewer = reviewer
        refund.review_remark = review_remark
        refund.reviewed_at = timezone.now()
        refund.save(update_fields=['status', 'reviewer', 'review_remark', 'reviewed_at', 'updated_at'])

        NotificationService.create_user_notification(
            user=refund.user,
            title=notify_title,
            content=notify_content,
            notice_type='order',
        )

        return refund

    @staticmethod
    def get_refundable_recharges(user):
        from django.db.models import OuterRef, Subquery, Sum, Value
        from django.db.models.functions import Coalesce

        refunded_subq = (
            RefundRequest.objects.filter(
                recharge_record=OuterRef('pk'),
                status__in=[RefundRequest.STATUS_PENDING, RefundRequest.STATUS_APPROVED],
            )
            .values('recharge_record')
            .annotate(total=Sum('amount'))
            .values('total')
        )

        qs = (
            RechargeRecord.objects.filter(user=user)
            .annotate(refunded_amount=Coalesce(Subquery(refunded_subq), Value(Decimal('0.00'))))
            .order_by('-created_at')
        )
        result = []
        for r in qs:
            remaining = RefundService._money(r.amount - (r.refunded_amount or 0))
            if remaining > 0:
                result.append(r)
                r.remaining_amount = remaining
        return result
