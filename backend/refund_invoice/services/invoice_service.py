from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from billing.models import RechargeRecord
from notices.services import NotificationService
from refund_invoice.models import (
    InvoiceRequest,
    InvoiceRequestItem,
    InvoiceTitle,
    RefundRequest,
)


class InvoiceService:
    @staticmethod
    def _money(value: Decimal) -> Decimal:
        return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @staticmethod
    def _next_invoice_no() -> str:
        return f'IV{timezone.now().strftime("%Y%m%d%H%M%S")}{uuid4().hex[:6].upper()}'

    @staticmethod
    def _get_invoiced_amount(recharge_record: RechargeRecord, exclude_id: int | None = None) -> Decimal:
        qs = InvoiceRequestItem.objects.filter(
            recharge_record=recharge_record,
            invoice_request__status__in=[
                InvoiceRequest.STATUS_PENDING,
                InvoiceRequest.STATUS_ISSUED,
            ],
        )
        if exclude_id:
            qs = qs.exclude(invoice_request_id=exclude_id)
        total = qs.aggregate(total=__import__('django.db.models', fromlist=['Sum']).Sum('amount')).get('total')
        return InvoiceService._money(total or 0)

    @staticmethod
    def _get_refunded_amount(recharge_record: RechargeRecord) -> Decimal:
        total = (
            RefundRequest.objects.filter(
                recharge_record=recharge_record,
                status=RefundRequest.STATUS_APPROVED,
            )
            .aggregate(total=__import__('django.db.models', fromlist=['Sum']).Sum('amount'))
            .get('total')
        )
        return InvoiceService._money(total or 0)

    @staticmethod
    @transaction.atomic
    def create_title(
        user,
        title_type: str,
        title_name: str,
        email: str,
        tax_no: str = '',
        is_default: bool = False,
    ) -> InvoiceTitle:
        if title_type == InvoiceTitle.TYPE_COMPANY and not tax_no:
            raise ValidationError('单位抬头必须填写纳税人识别号。')

        if is_default:
            InvoiceTitle.objects.filter(user=user).update(is_default=False)
        elif not InvoiceTitle.objects.filter(user=user).exists():
            is_default = True

        title = InvoiceTitle.objects.create(
            user=user,
            title_type=title_type,
            title_name=title_name,
            tax_no=tax_no,
            email=email,
            is_default=is_default,
        )
        return title

    @staticmethod
    @transaction.atomic
    def update_title(
        user,
        title_id: int,
        title_type: str | None = None,
        title_name: str | None = None,
        email: str | None = None,
        tax_no: str | None = None,
        is_default: bool | None = None,
    ) -> InvoiceTitle:
        title = InvoiceTitle.objects.filter(id=title_id, user=user).first()
        if not title:
            raise ValidationError('发票抬头不存在。')

        if title_type is not None:
            title.title_type = title_type
        if title_name is not None:
            title.title_name = title_name
        if email is not None:
            title.email = email
        if tax_no is not None:
            title.tax_no = tax_no
        if is_default is not None:
            if is_default:
                InvoiceTitle.objects.filter(user=user).exclude(pk=title_id).update(is_default=False)
            title.is_default = is_default

        if title.title_type == InvoiceTitle.TYPE_COMPANY and not title.tax_no:
            raise ValidationError('单位抬头必须填写纳税人识别号。')

        title.save()
        return title

    @staticmethod
    @transaction.atomic
    def delete_title(user, title_id: int) -> None:
        title = InvoiceTitle.objects.filter(id=title_id, user=user).first()
        if not title:
            raise ValidationError('发票抬头不存在。')
        if title.invoice_requests.exists():
            raise ValidationError('该抬头已被开票申请使用，无法删除。')
        title.delete()

    @staticmethod
    @transaction.atomic
    def set_default_title(user, title_id: int) -> InvoiceTitle:
        title = InvoiceTitle.objects.filter(id=title_id, user=user).first()
        if not title:
            raise ValidationError('发票抬头不存在。')
        InvoiceTitle.objects.filter(user=user).update(is_default=False)
        title.is_default = True
        title.save(update_fields=['is_default', 'updated_at'])
        return title

    @staticmethod
    def get_invoiceable_recharges(user):
        from django.db.models import OuterRef, Subquery, Sum, Value
        from django.db.models.functions import Coalesce

        invoiced_subq = (
            InvoiceRequestItem.objects.filter(
                recharge_record=OuterRef('pk'),
                invoice_request__status__in=[
                    InvoiceRequest.STATUS_PENDING,
                    InvoiceRequest.STATUS_ISSUED,
                ],
            )
            .values('recharge_record')
            .annotate(total=Sum('amount'))
            .values('total')
        )
        refunded_subq = (
            RefundRequest.objects.filter(
                recharge_record=OuterRef('pk'),
                status=RefundRequest.STATUS_APPROVED,
            )
            .values('recharge_record')
            .annotate(total=Sum('amount'))
            .values('total')
        )

        qs = (
            RechargeRecord.objects.filter(user=user)
            .annotate(
                invoiced_amount=Coalesce(Subquery(invoiced_subq), Value(Decimal('0.00'))),
                refunded_amount=Coalesce(Subquery(refunded_subq), Value(Decimal('0.00'))),
            )
            .order_by('-created_at')
        )
        result = []
        for r in qs:
            remaining = InvoiceService._money(r.amount - (r.invoiced_amount or 0) - (r.refunded_amount or 0))
            if remaining > 0:
                r.remaining_invoiceable = remaining
                result.append(r)
        return result

    @staticmethod
    @transaction.atomic
    def create_invoice_request(
        user,
        title_id: int,
        items: list[dict],
        remark: str = '',
    ) -> InvoiceRequest:
        if not items:
            raise ValidationError('请选择要开票的充值记录。')

        title = InvoiceTitle.objects.filter(id=title_id, user=user).first()
        if not title:
            raise ValidationError('发票抬头不存在。')

        total_amount = Decimal('0.00')
        item_list = []

        for item in items:
            recharge_id = item.get('recharge_record_id')
            amount = InvoiceService._money(item.get('amount', 0))

            if amount <= 0:
                raise ValidationError('每笔开票金额必须大于 0。')

            recharge = (
                RechargeRecord.objects.select_for_update()
                .filter(id=recharge_id, user=user)
                .first()
            )
            if not recharge:
                raise ValidationError('充值记录不存在或不属于您。')

            invoiced = InvoiceService._get_invoiced_amount(recharge)
            refunded = InvoiceService._get_refunded_amount(recharge)
            remaining = InvoiceService._money(recharge.amount - invoiced - refunded)
            if amount > remaining:
                raise ValidationError(
                    f'充值记录 #{recharge.id} 剩余可开票金额为 ¥{remaining}。'
                )

            total_amount = InvoiceService._money(total_amount + amount)
            item_list.append({'recharge': recharge, 'amount': amount})

        if total_amount <= 0:
            raise ValidationError('开票总金额必须大于 0。')

        request = InvoiceRequest.objects.create(
            invoice_no=InvoiceService._next_invoice_no(),
            user=user,
            title=title,
            total_amount=total_amount,
            remark=remark,
        )

        for item in item_list:
            InvoiceRequestItem.objects.create(
                invoice_request=request,
                recharge_record=item['recharge'],
                amount=item['amount'],
            )

        return request

    @staticmethod
    @transaction.atomic
    def process_invoice(
        invoice: InvoiceRequest,
        action: str,
        reviewer,
        invoice_number: str = '',
        download_url: str = '',
        review_remark: str = '',
    ) -> InvoiceRequest:
        invoice = (
            InvoiceRequest.objects.select_for_update()
            .select_related('user', 'title')
            .filter(id=invoice.id)
            .first()
        )
        if not invoice:
            raise ValidationError('开票申请不存在。')
        if invoice.status != InvoiceRequest.STATUS_PENDING:
            raise ValidationError('该开票申请已处理，请勿重复操作。')

        if action not in {InvoiceRequest.STATUS_ISSUED, InvoiceRequest.STATUS_REJECTED}:
            raise ValidationError('非法处理动作。')

        if action == InvoiceRequest.STATUS_ISSUED:
            if not invoice_number or not download_url:
                raise ValidationError('开具发票时必须填写发票号和下载链接。')
            invoice.invoice_number = invoice_number
            invoice.download_url = download_url
            notify_title = '发票已开具'
            notify_content = (
                f'开票申请 {invoice.invoice_no} 已完成，发票号：{invoice_number}。'
            )
        else:
            if not review_remark:
                raise ValidationError('驳回开票申请时必须填写原因。')
            notify_title = '开票申请被驳回'
            notify_content = f'开票申请 {invoice.invoice_no} 已被驳回。原因：{review_remark}'

        invoice.status = action
        invoice.reviewer = reviewer
        invoice.review_remark = review_remark
        invoice.reviewed_at = timezone.now()
        invoice.save(
            update_fields=[
                'status',
                'invoice_number',
                'download_url',
                'reviewer',
                'review_remark',
                'reviewed_at',
                'updated_at',
            ]
        )

        NotificationService.create_user_notification(
            user=invoice.user,
            title=notify_title,
            content=notify_content,
            notice_type='order',
        )

        return invoice

    @staticmethod
    @transaction.atomic
    def void_invoice(
        invoice: InvoiceRequest,
        reviewer,
        review_remark: str = '',
    ) -> InvoiceRequest:
        invoice = (
            InvoiceRequest.objects.select_for_update()
            .select_related('user')
            .filter(id=invoice.id)
            .first()
        )
        if not invoice:
            raise ValidationError('开票申请不存在。')
        if invoice.status != InvoiceRequest.STATUS_ISSUED:
            raise ValidationError('只能作废已开具的发票。')

        invoice.status = InvoiceRequest.STATUS_VOID
        invoice.reviewer = reviewer
        invoice.review_remark = review_remark
        invoice.reviewed_at = timezone.now()
        invoice.save(update_fields=['status', 'reviewer', 'review_remark', 'reviewed_at', 'updated_at'])

        NotificationService.create_user_notification(
            user=invoice.user,
            title='发票已作废',
            content=f'开票申请 {invoice.invoice_no} 对应的发票已作废。',
            notice_type='order',
        )

        return invoice
