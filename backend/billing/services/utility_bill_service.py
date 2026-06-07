from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from billing.models import BalanceChangeLog, MeterReading, UtilityBill, Wallet
from billing.services.ledger_service import LedgerService
from billing.services.price_service import PriceService
from billing.services.meter_service import MeterService
from notices.services import NotificationService


class UtilityBillService:
    LATE_FEE_RATE = Decimal('0.0005')
    LATE_FEE_GRACE_DAYS = 0
    DEFAULT_DUE_DAYS = 15

    @staticmethod
    def _money(value: Decimal) -> Decimal:
        return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @staticmethod
    def _next_bill_no() -> str:
        return f'UB{timezone.now().strftime("%Y%m%d%H%M%S")}{uuid4().hex[:6].upper()}'

    @staticmethod
    @transaction.atomic
    def create_bill_from_reading(
        reading: MeterReading,
        user,
        operator: str = 'system',
    ) -> UtilityBill | None:
        if reading.usage <= 0:
            return None

        base_amount, unit_price, price_detail = PriceService.calculate_cost(
            category=reading.category,
            usage=reading.usage,
        )

        due_date = reading.period_end + timedelta(days=UtilityBillService.DEFAULT_DUE_DAYS)

        bill = UtilityBill.objects.create(
            bill_no=UtilityBillService._next_bill_no(),
            user=user,
            room=reading.room,
            category=reading.category,
            period_start=reading.period_start,
            period_end=reading.period_end,
            previous_reading=reading.previous_reading,
            current_reading=reading.current_reading,
            usage=reading.usage,
            price_detail=price_detail,
            unit_price=unit_price,
            base_amount=base_amount,
            late_fee_amount=Decimal('0.00'),
            total_amount=base_amount,
            paid_amount=Decimal('0.00'),
            due_date=due_date,
            status=UtilityBill.STATUS_PENDING,
            meter_reading=reading,
            operator=operator,
        )

        NotificationService.create_user_notification(
            user=user,
            title=f'{bill.get_category_display()}账单已生成',
            content=f'{reading.period_start} 至 {reading.period_end} 的{bill.get_category_display()}账单已生成，应缴金额 ¥{bill.total_amount}，请在 {due_date} 前缴纳。',
            notice_type='billing',
        )

        return bill

    @staticmethod
    @transaction.atomic
    def generate_bills_from_reading(reading: MeterReading, operator: str = 'system') -> list:
        user_ids = MeterService.get_room_active_users(reading.room)
        if not user_ids:
            return []

        bills = []
        for user_id in user_ids:
            existing = UtilityBill.objects.filter(
                meter_reading=reading,
                user_id=user_id,
            ).first()
            if existing:
                continue

            bill = UtilityBillService.create_bill_from_reading(reading, user_id, operator)
            if bill:
                bills.append(bill)

        return bills

    @staticmethod
    @transaction.atomic
    def generate_bills_for_period(
        period_start,
        period_end,
        category: str | None = None,
        operator: str = 'system',
    ) -> list:
        readings = MeterReading.objects.filter(
            period_start=period_start,
            period_end=period_end,
        )
        if category:
            readings = readings.filter(category=category)

        all_bills = []
        for reading in readings:
            bills = UtilityBillService.generate_bills_from_reading(reading, operator)
            all_bills.extend(bills)

        return all_bills

    @staticmethod
    @transaction.atomic
    def pay_bill(bill: UtilityBill, payer, operator: str | None = None) -> UtilityBill:
        bill = UtilityBill.objects.select_for_update().select_related('user', 'room').filter(id=bill.id).first()
        if not bill:
            raise ValidationError('账单不存在。')

        if bill.status not in (UtilityBill.STATUS_PENDING, UtilityBill.STATUS_OVERDUE):
            raise ValidationError(f'当前账单状态为「{bill.get_status_display()}」，无法缴纳。')

        if bill.outstanding_amount <= 0:
            bill.status = UtilityBill.STATUS_PAID
            bill.save(update_fields=['status', 'updated_at'])
            return bill

        wallet, _ = Wallet.objects.select_for_update().get_or_create(user=bill.user)
        if wallet.is_frozen:
            raise ValidationError('账户已冻结，无法缴费。')

        if wallet.balance < bill.outstanding_amount:
            raise ValidationError(f'余额不足。应缴 ¥{bill.outstanding_amount}，当前余额 ¥{wallet.balance}。')

        if payer.id != bill.user_id:
            wallet_payer, _ = Wallet.objects.select_for_update().get_or_create(user=payer)
            if wallet_payer.is_frozen:
                raise ValidationError('支付账户已冻结。')
            if wallet_payer.balance < bill.outstanding_amount:
                raise ValidationError(f'余额不足。应缴 ¥{bill.outstanding_amount}，当前余额 ¥{wallet_payer.balance}。')
            wallet = wallet_payer

        balance_before = wallet.balance
        pay_amount = bill.outstanding_amount
        wallet.balance = UtilityBillService._money(wallet.balance - pay_amount)
        wallet.save(update_fields=['balance', 'updated_at'])

        consumption = LedgerService.create_consumption(
            user=bill.user,
            category=bill.category,
            usage=bill.usage,
            unit_price=bill.unit_price,
            meter_value=bill.current_reading,
            operator=operator or payer.username,
            remark=f'缴纳账单 {bill.bill_no}',
        )

        bill.paid_amount = bill.total_amount
        bill.status = UtilityBill.STATUS_PAID
        bill.paid_at = timezone.now()
        bill.consumption_record = consumption
        bill.operator = operator or payer.username
        bill.save(
            update_fields=[
                'paid_amount',
                'status',
                'paid_at',
                'consumption_record',
                'operator',
                'updated_at',
            ]
        )

        BalanceChangeLog.objects.create(
            user=wallet.user,
            wallet=wallet,
            change_type=BalanceChangeLog.TYPE_CONSUMPTION,
            amount_delta=UtilityBillService._money(-pay_amount),
            balance_before=UtilityBillService._money(balance_before),
            balance_after=UtilityBillService._money(wallet.balance),
            related_order_no=bill.bill_no,
            operator=operator or payer.username,
            remark=f'缴纳{bill.get_category_display()}账单 {bill.bill_no}',
        )

        NotificationService.create_user_notification(
            user=bill.user,
            title=f'{bill.get_category_display()}账单已缴纳',
            content=f'账单 {bill.bill_no} 已成功缴纳，金额 ¥{pay_amount}。',
            notice_type='billing',
        )

        return bill

    @staticmethod
    @transaction.atomic
    def calculate_late_fee(bill: UtilityBill, apply: bool = True) -> Decimal:
        bill = UtilityBill.objects.select_for_update().filter(id=bill.id).first()
        if not bill:
            return Decimal('0.00')

        if bill.status in (UtilityBill.STATUS_PAID, UtilityBill.STATUS_VOID, UtilityBill.STATUS_MERGED):
            return bill.late_fee_amount

        today = timezone.now().date()
        if today <= bill.due_date + timedelta(days=UtilityBillService.LATE_FEE_GRACE_DAYS):
            return bill.late_fee_amount

        overdue_days = (today - bill.due_date - timedelta(days=UtilityBillService.LATE_FEE_GRACE_DAYS)).days
        if overdue_days <= 0:
            return bill.late_fee_amount

        new_late_fee = UtilityBillService._money(
            bill.base_amount * UtilityBillService.LATE_FEE_RATE * overdue_days
        )

        if apply and new_late_fee != bill.late_fee_amount:
            bill.late_fee_amount = new_late_fee
            bill.total_amount = UtilityBillService._money(bill.base_amount + new_late_fee)
            if bill.status == UtilityBill.STATUS_PENDING:
                bill.status = UtilityBill.STATUS_OVERDUE
            bill.save(update_fields=['late_fee_amount', 'total_amount', 'status', 'updated_at'])

        return new_late_fee

    @staticmethod
    def run_late_fee_batch() -> int:
        overdue_bills = UtilityBill.objects.filter(
            status__in=[UtilityBill.STATUS_PENDING, UtilityBill.STATUS_OVERDUE],
            due_date__lt=timezone.now().date(),
        )
        count = 0
        for bill in overdue_bills:
            try:
                UtilityBillService.calculate_late_fee(bill, apply=True)
                count += 1
            except Exception:
                continue
        return count

    @staticmethod
    @transaction.atomic
    def void_bill(bill: UtilityBill, operator, remark: str = '') -> UtilityBill:
        bill = UtilityBill.objects.select_for_update().filter(id=bill.id).first()
        if not bill:
            raise ValidationError('账单不存在。')

        if bill.status == UtilityBill.STATUS_PAID:
            raise ValidationError('已缴纳的账单不能作废，请先处理退款。')

        if bill.status == UtilityBill.STATUS_VOID:
            return bill

        bill.status = UtilityBill.STATUS_VOID
        bill.operator = operator.username
        bill.remark = remark or bill.remark
        bill.save(update_fields=['status', 'operator', 'remark', 'updated_at'])

        NotificationService.create_user_notification(
            user=bill.user,
            title=f'{bill.get_category_display()}账单已作废',
            content=f'账单 {bill.bill_no} 已被管理员作废。',
            notice_type='billing',
        )

        return bill

    @staticmethod
    @transaction.atomic
    def merge_bills(bills: list[UtilityBill], operator) -> UtilityBill:
        if len(bills) < 2:
            raise ValidationError('至少需要选择 2 张账单进行合并。')

        user_ids = set(b.user_id for b in bills)
        if len(user_ids) > 1:
            raise ValidationError('只能合并同一用户的账单。')

        categories = set(b.category for b in bills)
        if len(categories) > 1:
            raise ValidationError('只能合并相同类型的账单。')

        for bill in bills:
            if bill.status not in (UtilityBill.STATUS_PENDING, UtilityBill.STATUS_OVERDUE):
                raise ValidationError(
                    f'账单 {bill.bill_no} 状态为「{bill.get_status_display()}」，无法合并。'
                )

        merged_bill = UtilityBill.objects.select_for_update().filter(id=bills[0].id).first()
        if not merged_bill:
            raise ValidationError('账单不存在。')

        total_base = Decimal('0.00')
        total_late = Decimal('0.00')
        total_paid = Decimal('0.00')
        total_usage = Decimal('0.00')
        price_details = []

        for bill in bills:
            UtilityBillService.calculate_late_fee(bill, apply=True)
            b = UtilityBill.objects.select_for_update().filter(id=bill.id).first()
            total_base += b.base_amount
            total_late += b.late_fee_amount
            total_paid += b.paid_amount
            total_usage += b.usage
            price_details.append(
                {
                    'bill_no': b.bill_no,
                    'period': f'{b.period_start} ~ {b.period_end}',
                    'base_amount': str(b.base_amount),
                    'late_fee': str(b.late_fee_amount),
                }
            )
            if b.id != merged_bill.id:
                b.status = UtilityBill.STATUS_MERGED
                b.parent_bill = merged_bill
                b.operator = operator.username
                b.save(update_fields=['status', 'parent_bill', 'operator', 'updated_at'])

        merged_bill.base_amount = UtilityBillService._money(total_base)
        merged_bill.late_fee_amount = UtilityBillService._money(total_late)
        merged_bill.total_amount = UtilityBillService._money(total_base + total_late)
        merged_bill.paid_amount = UtilityBillService._money(total_paid)
        merged_bill.usage = total_usage
        merged_bill.price_detail = {'merged': True, 'bills': price_details}
        merged_bill.operator = operator.username
        merged_bill.save(
            update_fields=[
                'base_amount',
                'late_fee_amount',
                'total_amount',
                'paid_amount',
                'usage',
                'price_detail',
                'operator',
                'updated_at',
            ]
        )

        NotificationService.create_user_notification(
            user=merged_bill.user,
            title='账单已合并',
            content=f'{len(bills)} 张账单已合并至 {merged_bill.bill_no}，合并后应缴金额 ¥{merged_bill.outstanding_amount}。',
            notice_type='billing',
        )

        return merged_bill

    @staticmethod
    @transaction.atomic
    def regenerate_bill(bill: UtilityBill, operator) -> UtilityBill:
        if bill.status == UtilityBill.STATUS_PAID:
            raise ValidationError('已缴纳的账单不能重新生成。')

        reading = bill.meter_reading
        if not reading:
            raise ValidationError('该账单没有关联的抄表记录，无法重新生成。')

        base_amount, unit_price, price_detail = PriceService.calculate_cost(
            category=bill.category,
            usage=reading.usage,
        )

        bill.previous_reading = reading.previous_reading
        bill.current_reading = reading.current_reading
        bill.usage = reading.usage
        bill.price_detail = price_detail
        bill.unit_price = unit_price
        bill.base_amount = base_amount
        bill.late_fee_amount = Decimal('0.00')
        bill.total_amount = base_amount
        bill.status = UtilityBill.STATUS_PENDING
        bill.operator = operator.username
        bill.save(
            update_fields=[
                'previous_reading',
                'current_reading',
                'usage',
                'price_detail',
                'unit_price',
                'base_amount',
                'late_fee_amount',
                'total_amount',
                'status',
                'operator',
                'updated_at',
            ]
        )

        return bill
