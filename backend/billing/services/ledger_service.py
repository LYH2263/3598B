from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from billing.models import (
    BalanceChangeLog,
    ConsumptionRecord,
    RechargeOrder,
    RechargeRecord,
    Wallet,
)
from notices.services import NotificationService


class LedgerService:
    @staticmethod
    def _money(value: Decimal) -> Decimal:
        return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @staticmethod
    def _next_order_no() -> str:
        return f'RC{timezone.now().strftime("%Y%m%d%H%M%S")}{uuid4().hex[:6].upper()}'

    @staticmethod
    def _create_balance_log(
        *,
        wallet: Wallet,
        change_type: str,
        amount_delta: Decimal,
        balance_before: Decimal,
        balance_after: Decimal,
        operator: str,
        related_order_no: str = '',
        remark: str = '',
    ) -> BalanceChangeLog:
        return BalanceChangeLog.objects.create(
            user=wallet.user,
            wallet=wallet,
            change_type=change_type,
            amount_delta=LedgerService._money(amount_delta),
            balance_before=LedgerService._money(balance_before),
            balance_after=LedgerService._money(balance_after),
            operator=operator,
            related_order_no=related_order_no,
            remark=remark,
        )

    @staticmethod
    @transaction.atomic
    def create_recharge(user, amount: Decimal, channel: str, operator: str, remark: str = '', order=None):
        amount = LedgerService._money(amount)
        if amount <= 0:
            raise ValidationError('充值金额必须大于 0。')

        wallet, _ = Wallet.objects.select_for_update().get_or_create(user=user)
        if wallet.is_frozen:
            raise ValidationError('账户已冻结，无法执行充值入账。')

        balance_before = wallet.balance
        wallet.balance = LedgerService._money(wallet.balance + amount)
        wallet.save(update_fields=['balance', 'updated_at'])

        record = RechargeRecord.objects.create(
            user=user,
            order=order,
            amount=amount,
            channel=channel,
            operator=operator,
            remark=remark,
        )

        LedgerService._create_balance_log(
            wallet=wallet,
            change_type=BalanceChangeLog.TYPE_RECHARGE,
            amount_delta=amount,
            balance_before=balance_before,
            balance_after=wallet.balance,
            operator=operator,
            related_order_no=order.order_no if order else '',
            remark=remark,
        )

        return record

    @staticmethod
    @transaction.atomic
    def create_recharge_order(user, amount: Decimal, channel: str, submit_remark: str = ''):
        amount = LedgerService._money(amount)
        if amount <= 0:
            raise ValidationError('充值金额必须大于 0。')

        wallet, _ = Wallet.objects.select_for_update().get_or_create(user=user)
        if wallet.is_frozen:
            raise ValidationError('账户已冻结，无法提交充值订单。')

        return RechargeOrder.objects.create(
            user=user,
            order_no=LedgerService._next_order_no(),
            amount=amount,
            channel=channel,
            submit_remark=submit_remark,
        )

    @staticmethod
    @transaction.atomic
    def review_recharge_order(order: RechargeOrder, action: str, reviewer, review_remark: str = '') -> RechargeOrder:
        order = RechargeOrder.objects.select_for_update().select_related('user').filter(id=order.id).first()
        if not order:
            raise ValidationError('充值订单不存在。')
        if order.status != RechargeOrder.STATUS_PENDING:
            raise ValidationError('该充值订单已处理，请勿重复审核。')

        if action not in {RechargeOrder.STATUS_APPROVED, RechargeOrder.STATUS_REJECTED}:
            raise ValidationError('非法审核动作。')

        if action == RechargeOrder.STATUS_APPROVED:
            LedgerService.create_recharge(
                user=order.user,
                amount=order.amount,
                channel=order.channel,
                operator=reviewer.username,
                remark=review_remark or '管理员审核通过充值订单',
                order=order,
            )
            order.status = RechargeOrder.STATUS_APPROVED
            notify_title = '充值订单审核通过'
            notify_content = f'订单 {order.order_no} 已审核通过，金额 ¥{order.amount} 已入账。'
        else:
            order.status = RechargeOrder.STATUS_REJECTED
            notify_title = '充值订单被驳回'
            notify_content = f'订单 {order.order_no} 已被驳回，请联系管理员。'

        order.reviewer = reviewer
        order.review_remark = review_remark
        order.reviewed_at = timezone.now()
        order.save(update_fields=['status', 'reviewer', 'review_remark', 'reviewed_at', 'updated_at'])

        NotificationService.create_user_notification(
            user=order.user,
            title=notify_title,
            content=notify_content,
            notice_type='order',
        )

        return order

    @staticmethod
    @transaction.atomic
    def freeze_wallet(user, operator: str, reason: str = '') -> Wallet:
        wallet, _ = Wallet.objects.select_for_update().get_or_create(user=user)
        if wallet.is_frozen:
            return wallet

        balance_before = wallet.balance
        wallet.is_frozen = True
        wallet.frozen_reason = reason
        wallet.frozen_at = timezone.now()
        wallet.save(update_fields=['is_frozen', 'frozen_reason', 'frozen_at', 'updated_at'])

        LedgerService._create_balance_log(
            wallet=wallet,
            change_type=BalanceChangeLog.TYPE_FREEZE,
            amount_delta=Decimal('0.00'),
            balance_before=balance_before,
            balance_after=wallet.balance,
            operator=operator,
            remark=reason or '管理员冻结账户',
        )

        NotificationService.create_user_notification(
            user=user,
            title='账户已冻结',
            content='您的账户已被冻结，暂无法进行充值或消费，请联系管理员。',
            notice_type='security',
        )

        return wallet

    @staticmethod
    @transaction.atomic
    def unfreeze_wallet(user, operator: str, reason: str = '') -> Wallet:
        wallet, _ = Wallet.objects.select_for_update().get_or_create(user=user)
        if not wallet.is_frozen:
            return wallet

        balance_before = wallet.balance
        wallet.is_frozen = False
        wallet.frozen_reason = ''
        wallet.frozen_at = None
        wallet.save(update_fields=['is_frozen', 'frozen_reason', 'frozen_at', 'updated_at'])

        LedgerService._create_balance_log(
            wallet=wallet,
            change_type=BalanceChangeLog.TYPE_UNFREEZE,
            amount_delta=Decimal('0.00'),
            balance_before=balance_before,
            balance_after=wallet.balance,
            operator=operator,
            remark=reason or '管理员解冻账户',
        )

        NotificationService.create_user_notification(
            user=user,
            title='账户已解冻',
            content='您的账户已解除冻结，可正常进行充值与消费。',
            notice_type='security',
        )

        return wallet

    @staticmethod
    @transaction.atomic
    def create_consumption(
        user,
        category: str,
        usage: Decimal,
        unit_price: Decimal,
        meter_value: Decimal | None,
        operator: str,
        remark: str = '',
    ):
        usage = LedgerService._money(usage)
        unit_price = LedgerService._money(unit_price)
        if usage <= 0 or unit_price <= 0:
            raise ValidationError('用量和单价必须大于 0。')

        wallet, _ = Wallet.objects.select_for_update().get_or_create(user=user)
        if wallet.is_frozen:
            raise ValidationError('账户已冻结，无法执行消费扣费。')

        cost_amount = LedgerService._money(usage * unit_price)
        if wallet.balance < cost_amount:
            raise ValidationError('余额不足，请先充值。')

        balance_before = wallet.balance
        wallet.balance = LedgerService._money(wallet.balance - cost_amount)
        wallet.save(update_fields=['balance', 'updated_at'])

        record = ConsumptionRecord.objects.create(
            user=user,
            category=category,
            usage=usage,
            unit_price=unit_price,
            cost_amount=cost_amount,
            meter_value=meter_value,
            operator=operator,
            remark=remark,
        )

        LedgerService._create_balance_log(
            wallet=wallet,
            change_type=BalanceChangeLog.TYPE_CONSUMPTION,
            amount_delta=LedgerService._money(-cost_amount),
            balance_before=balance_before,
            balance_after=wallet.balance,
            operator=operator,
            remark=remark,
        )

        return record
