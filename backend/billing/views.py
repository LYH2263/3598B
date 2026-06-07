from datetime import datetime

from django.contrib.auth.models import User
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Profile
from accounts.permissions import IsAdminRole
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
from billing.serializers import (
    BalanceChangeLogSerializer,
    BillBatchGenerateSerializer,
    BillMergeSerializer,
    BillPaySerializer,
    BillRegenerateSerializer,
    BillVoidSerializer,
    ConsumptionCreateSerializer,
    ConsumptionRecordSerializer,
    MeterReadingCreateSerializer,
    MeterReadingSerializer,
    PriceStrategySerializer,
    RechargeCreateSerializer,
    RechargeOrderCreateSerializer,
    RechargeOrderReviewSerializer,
    RechargeOrderSerializer,
    RechargeRecordSerializer,
    UtilityBillSerializer,
    WalletActionSerializer,
    WalletSerializer,
)
from billing.services.ledger_service import LedgerService
from billing.services.utility_bill_service import UtilityBillService


class DashboardAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        wallet, _ = Wallet.objects.get_or_create(user=user)

        recharge_total = user.recharges.aggregate(total=Sum('amount')).get('total') or 0
        consumption_total = user.consumptions.aggregate(total=Sum('cost_amount')).get('total') or 0

        recharges = RechargeRecord.objects.filter(user=user)[:5]
        consumptions = ConsumptionRecord.objects.filter(user=user)[:5]
        pending_orders = RechargeOrder.objects.filter(user=user, status=RechargeOrder.STATUS_PENDING).count()

        return Response(
            {
                'wallet': WalletSerializer(wallet).data,
                'summary': {
                    'total_recharge': recharge_total,
                    'total_consumption': consumption_total,
                    'pending_recharge_orders': pending_orders,
                },
                'recent_recharges': RechargeRecordSerializer(recharges, many=True).data,
                'recent_consumptions': ConsumptionRecordSerializer(consumptions, many=True).data,
            }
        )


class RechargeListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self, request):
        role = getattr(request.user.profile, 'role', Profile.ROLE_STUDENT)
        if role == Profile.ROLE_ADMIN:
            return RechargeRecord.objects.select_related('user').all()
        return RechargeRecord.objects.select_related('user').filter(user=request.user)

    def get(self, request):
        queryset = self.get_queryset(request)[:100]
        return Response(RechargeRecordSerializer(queryset, many=True).data)

    def post(self, request):
        serializer = RechargeCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        record = serializer.save()
        return Response(RechargeRecordSerializer(record).data, status=status.HTTP_201_CREATED)


class RechargeOrderListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self, request):
        role = getattr(request.user.profile, 'role', Profile.ROLE_STUDENT)
        queryset = RechargeOrder.objects.select_related('user', 'reviewer')
        if role == Profile.ROLE_ADMIN:
            return queryset.all()
        return queryset.filter(user=request.user)

    def get(self, request):
        queryset = self.get_queryset(request)
        status_filter = request.query_params.get('status', '').strip()
        user_id = request.query_params.get('user_id', '').strip()

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if user_id and getattr(request.user.profile, 'role', '') == Profile.ROLE_ADMIN:
            queryset = queryset.filter(user_id=user_id)

        return Response(RechargeOrderSerializer(queryset[:200], many=True).data)

    def post(self, request):
        role = getattr(request.user.profile, 'role', Profile.ROLE_STUDENT)
        if role != Profile.ROLE_STUDENT:
            return Response({'detail': '仅学生可提交充值订单。'}, status=status.HTTP_403_FORBIDDEN)

        serializer = RechargeOrderCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(RechargeOrderSerializer(order).data, status=status.HTTP_201_CREATED)


class RechargeOrderReviewAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def post(self, request, order_id: int):
        order = RechargeOrder.objects.filter(id=order_id).first()
        if not order:
            return Response({'detail': '充值订单不存在。'}, status=status.HTTP_404_NOT_FOUND)

        serializer = RechargeOrderReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reviewed_order = LedgerService.review_recharge_order(
            order=order,
            action=serializer.validated_data['action'],
            reviewer=request.user,
            review_remark=serializer.validated_data.get('review_remark', ''),
        )
        return Response(RechargeOrderSerializer(reviewed_order).data)


class ConsumptionListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self, request):
        role = getattr(request.user.profile, 'role', Profile.ROLE_STUDENT)
        queryset = ConsumptionRecord.objects.select_related('user').all()
        if role != Profile.ROLE_ADMIN:
            queryset = queryset.filter(user=request.user)

        category = request.query_params.get('category', '').strip()
        start_date = request.query_params.get('start_date', '').strip()
        end_date = request.query_params.get('end_date', '').strip()
        user_id = request.query_params.get('user_id', '').strip()

        if category:
            queryset = queryset.filter(category=category)
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        if user_id and role == Profile.ROLE_ADMIN:
            queryset = queryset.filter(user_id=user_id)

        return queryset

    def get(self, request):
        queryset = self.get_queryset(request)[:200]
        return Response(ConsumptionRecordSerializer(queryset, many=True).data)

    def post(self, request):
        serializer = ConsumptionCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        record = serializer.save()
        return Response(ConsumptionRecordSerializer(record).data, status=status.HTTP_201_CREATED)


class ConsumptionStatsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        role = getattr(request.user.profile, 'role', Profile.ROLE_STUDENT)
        queryset = ConsumptionRecord.objects.all()
        if role != Profile.ROLE_ADMIN:
            queryset = queryset.filter(user=request.user)

        start_date = request.query_params.get('start_date', '').strip()
        end_date = request.query_params.get('end_date', '').strip()
        user_id = request.query_params.get('user_id', '').strip()

        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        if user_id and role == Profile.ROLE_ADMIN:
            queryset = queryset.filter(user_id=user_id)

        category_stats = (
            queryset.values('category')
            .annotate(total_cost=Sum('cost_amount'), total_usage=Sum('usage'), count=Count('id'))
            .order_by('category')
        )

        trend = (
            queryset.annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(total_cost=Sum('cost_amount'))
            .order_by('day')
        )

        return Response(
            {
                'category_stats': list(category_stats),
                'daily_trend': [
                    {
                        'day': item['day'].strftime('%Y-%m-%d') if item['day'] else '',
                        'total_cost': item['total_cost'] or 0,
                    }
                    for item in trend
                ],
            }
        )


class WalletActionAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def post(self, request, user_id: int):
        target_user = User.objects.filter(id=user_id).first()
        if not target_user:
            return Response({'detail': '用户不存在。'}, status=status.HTTP_404_NOT_FOUND)

        serializer = WalletActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data['action']
        reason = serializer.validated_data.get('reason', '')

        if action == 'freeze':
            wallet = LedgerService.freeze_wallet(target_user, request.user.username, reason)
        else:
            wallet = LedgerService.unfreeze_wallet(target_user, request.user.username, reason)

        return Response({'wallet': WalletSerializer(wallet).data})


class WalletLogListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        role = getattr(request.user.profile, 'role', Profile.ROLE_STUDENT)
        queryset = BalanceChangeLog.objects.select_related('user')

        if role != Profile.ROLE_ADMIN:
            queryset = queryset.filter(user=request.user)

        user_id = request.query_params.get('user_id', '').strip()
        change_type = request.query_params.get('change_type', '').strip()
        if user_id and role == Profile.ROLE_ADMIN:
            queryset = queryset.filter(user_id=user_id)
        if change_type:
            queryset = queryset.filter(change_type=change_type)

        return Response(BalanceChangeLogSerializer(queryset[:300], many=True).data)


class PriceStrategyListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get(self, request):
        queryset = PriceStrategy.objects.all()
        return Response(PriceStrategySerializer(queryset, many=True).data)

    def post(self, request):
        serializer = PriceStrategySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PriceStrategyDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def put(self, request, pk: int):
        strategy = PriceStrategy.objects.filter(pk=pk).first()
        if not strategy:
            return Response({'detail': '价格策略不存在。'}, status=status.HTTP_404_NOT_FOUND)
        serializer = PriceStrategySerializer(strategy, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class MeterReadingListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self, request):
        role = getattr(request.user.profile, 'role', Profile.ROLE_STUDENT)
        queryset = MeterReading.objects.select_related('room', 'room__building', 'user')

        if role != Profile.ROLE_ADMIN:
            from dormitory.models import RoomAssignment
            room_ids = list(
                RoomAssignment.objects.filter(user=request.user, unbound_at__isnull=True)
                .values_list('room_id', flat=True)
            )
            queryset = queryset.filter(room_id__in=room_ids)

        return queryset

    def get(self, request):
        queryset = self.get_queryset(request)

        category = request.query_params.get('category', '').strip()
        room_id = request.query_params.get('room_id', '').strip()
        start_date = request.query_params.get('start_date', '').strip()
        end_date = request.query_params.get('end_date', '').strip()

        if category:
            queryset = queryset.filter(category=category)
        if room_id:
            queryset = queryset.filter(room_id=room_id)
        if start_date:
            queryset = queryset.filter(period_end__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(period_start__date__lte=end_date)

        return Response(MeterReadingSerializer(queryset[:200], many=True).data)

    def post(self, request):
        role = getattr(request.user.profile, 'role', Profile.ROLE_STUDENT)
        if role != Profile.ROLE_ADMIN:
            return Response({'detail': '仅管理员可录入抄表数据。'}, status=status.HTTP_403_FORBIDDEN)

        serializer = MeterReadingCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        reading = serializer.save()
        return Response(MeterReadingSerializer(reading).data, status=status.HTTP_201_CREATED)


class UtilityBillListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self, request):
        role = getattr(request.user.profile, 'role', Profile.ROLE_STUDENT)
        queryset = UtilityBill.objects.select_related('user', 'room', 'room__building')

        if role != Profile.ROLE_ADMIN:
            queryset = queryset.filter(user=request.user)

        return queryset

    def get(self, request):
        queryset = self.get_queryset(request)

        status_filter = request.query_params.get('status', '').strip()
        category = request.query_params.get('category', '').strip()
        user_id = request.query_params.get('user_id', '').strip()
        room_id = request.query_params.get('room_id', '').strip()
        start_date = request.query_params.get('start_date', '').strip()
        end_date = request.query_params.get('end_date', '').strip()
        overdue = request.query_params.get('overdue', '').strip()

        role = getattr(request.user.profile, 'role', Profile.ROLE_STUDENT)

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if category:
            queryset = queryset.filter(category=category)
        if user_id and role == Profile.ROLE_ADMIN:
            queryset = queryset.filter(user_id=user_id)
        if room_id and role == Profile.ROLE_ADMIN:
            queryset = queryset.filter(room_id=room_id)
        if start_date:
            queryset = queryset.filter(period_end__gte=start_date)
        if end_date:
            queryset = queryset.filter(period_start__lte=end_date)
        if overdue == 'true':
            from django.utils import timezone
            queryset = queryset.filter(
                Q(status__in=[UtilityBill.STATUS_PENDING, UtilityBill.STATUS_OVERDUE]),
                due_date__lt=timezone.now().date(),
            )

        bills = list(queryset[:300])
        for bill in bills:
            if bill.status in (UtilityBill.STATUS_PENDING, UtilityBill.STATUS_OVERDUE):
                UtilityBillService.calculate_late_fee(bill, apply=False)

        return Response(UtilityBillSerializer(bills, many=True).data)


class UtilityBillDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk: int):
        role = getattr(request.user.profile, 'role', Profile.ROLE_STUDENT)
        bill = (
            UtilityBill.objects.select_related('user', 'room', 'room__building', 'meter_reading')
            .filter(pk=pk)
            .first()
        )
        if not bill:
            return Response({'detail': '账单不存在。'}, status=status.HTTP_404_NOT_FOUND)

        if role != Profile.ROLE_ADMIN and bill.user_id != request.user.id:
            return Response({'detail': '无权查看此账单。'}, status=status.HTTP_403_FORBIDDEN)

        if bill.status in (UtilityBill.STATUS_PENDING, UtilityBill.STATUS_OVERDUE):
            UtilityBillService.calculate_late_fee(bill, apply=True)

        return Response(UtilityBillSerializer(bill).data)


class BillPayAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = BillPaySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        bill_ids = serializer.validated_data['bill_ids']
        bills = UtilityBill.objects.filter(
            id__in=bill_ids,
            status__in=[UtilityBill.STATUS_PENDING, UtilityBill.STATUS_OVERDUE],
        )

        role = getattr(request.user.profile, 'role', Profile.ROLE_STUDENT)
        user_ids = set(bills.values_list('user_id', flat=True))

        if role != Profile.ROLE_ADMIN and user_ids and list(user_ids) != [request.user.id]:
            return Response({'detail': '只能缴纳自己的账单。'}, status=status.HTTP_403_FORBIDDEN)

        paid_bills = []
        errors = []

        for bill in bills:
            try:
                paid = UtilityBillService.pay_bill(bill, request.user)
                paid_bills.append(paid)
            except Exception as e:
                errors.append({'bill_id': bill.id, 'bill_no': bill.bill_no, 'error': str(e)})

        return Response(
            {
                'paid': UtilityBillSerializer(paid_bills, many=True).data,
                'errors': errors,
            }
        )


class BillVoidAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def post(self, request, pk: int):
        bill = UtilityBill.objects.filter(pk=pk).first()
        if not bill:
            return Response({'detail': '账单不存在。'}, status=status.HTTP_404_NOT_FOUND)

        serializer = BillVoidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        voided = UtilityBillService.void_bill(bill, request.user, serializer.validated_data.get('remark', ''))
        return Response(UtilityBillSerializer(voided).data)


class BillMergeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def post(self, request):
        serializer = BillMergeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        bill_ids = serializer.validated_data['bill_ids']
        bills = list(UtilityBill.objects.filter(id__in=bill_ids))

        if len(bills) != len(bill_ids):
            return Response({'detail': '部分账单不存在。'}, status=status.HTTP_400_BAD_REQUEST)

        merged = UtilityBillService.merge_bills(bills, request.user)
        return Response(UtilityBillSerializer(merged).data)


class BillRegenerateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def post(self, request, pk: int):
        bill = UtilityBill.objects.filter(pk=pk).first()
        if not bill:
            return Response({'detail': '账单不存在。'}, status=status.HTTP_404_NOT_FOUND)

        regenerated = UtilityBillService.regenerate_bill(bill, request.user)
        return Response(UtilityBillSerializer(regenerated).data)


class BillBatchGenerateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def post(self, request):
        serializer = BillBatchGenerateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        bills = serializer.save()
        return Response(
            {
                'count': len(bills),
                'bills': UtilityBillSerializer(bills, many=True).data,
            }
        )


class BillGenerateFromReadingAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def post(self, request, reading_id: int):
        reading = MeterReading.objects.filter(pk=reading_id).first()
        if not reading:
            return Response({'detail': '抄表记录不存在。'}, status=status.HTTP_404_NOT_FOUND)

        bills = UtilityBillService.generate_bills_from_reading(reading, request.user.username)
        return Response(
            {
                'count': len(bills),
                'bills': UtilityBillSerializer(bills, many=True).data,
            }
        )


class LateFeeRunAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def post(self, request):
        count = UtilityBillService.run_late_fee_batch()
        return Response({'processed_count': count})
