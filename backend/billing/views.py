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
    DashboardPreference,
    MeterReading,
    PriceStrategy,
    RechargeOrder,
    RechargeRecord,
    SavedReport,
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
    DashboardPreferenceSerializer,
    DatasetQuerySerializer,
    MeterReadingCreateSerializer,
    MeterReadingSerializer,
    PriceStrategySerializer,
    RechargeCreateSerializer,
    RechargeOrderCreateSerializer,
    RechargeOrderReviewSerializer,
    RechargeOrderSerializer,
    RechargeRecordSerializer,
    SavedReportSerializer,
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


class PlatformAnalyticsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get(self, request):
        from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, ExtractMonth
        from django.utils import timezone
        from datetime import timedelta

        window = request.query_params.get('window', '7d').strip()
        now = timezone.now()

        if window == '7d':
            start_date = now - timedelta(days=7)
            trunc_fn = TruncDate
        elif window == '30d':
            start_date = now - timedelta(days=30)
            trunc_fn = TruncDate
        elif window == '90d':
            start_date = now - timedelta(days=90)
            trunc_fn = TruncWeek
        elif window == '1y':
            start_date = now - timedelta(days=365)
            trunc_fn = TruncMonth
        else:
            start_date = now - timedelta(days=7)
            trunc_fn = TruncDate

        total_users = User.objects.count()
        active_users = User.objects.filter(last_login__gte=start_date).count()
        frozen_accounts = Wallet.objects.filter(is_frozen=True).count()
        pending_orders = RechargeOrder.objects.filter(status=RechargeOrder.STATUS_PENDING).count()

        total_recharge = RechargeRecord.objects.filter(created_at__gte=start_date).aggregate(
            total=Sum('amount')
        ).get('total') or 0
        total_consumption = ConsumptionRecord.objects.filter(created_at__gte=start_date).aggregate(
            total=Sum('cost_amount')
        ).get('total') or 0
        recharge_count = RechargeRecord.objects.filter(created_at__gte=start_date).count()
        consumption_count = ConsumptionRecord.objects.filter(created_at__gte=start_date).count()

        recharge_trend = list(
            RechargeRecord.objects.filter(created_at__gte=start_date)
            .annotate(period=trunc_fn('created_at'))
            .values('period')
            .annotate(amount=Sum('amount'), count=Count('id'))
            .order_by('period')
        )
        consumption_trend = list(
            ConsumptionRecord.objects.filter(created_at__gte=start_date)
            .annotate(period=trunc_fn('created_at'))
            .values('period')
            .annotate(amount=Sum('cost_amount'), count=Count('id'))
            .order_by('period')
        )
        user_growth_trend = list(
            User.objects.filter(date_joined__gte=start_date)
            .annotate(period=trunc_fn('date_joined'))
            .values('period')
            .annotate(count=Count('id'))
            .order_by('period')
        )

        recharge_by_channel = list(
            RechargeRecord.objects.filter(created_at__gte=start_date)
            .values('channel')
            .annotate(amount=Sum('amount'), count=Count('id'))
            .order_by('-amount')
        )
        consumption_by_category = list(
            ConsumptionRecord.objects.filter(created_at__gte=start_date)
            .values('category')
            .annotate(amount=Sum('cost_amount'), count=Count('id'))
            .order_by('-amount')
        )
        users_by_role = list(
            User.objects.values('profile__role')
            .annotate(count=Count('id'))
            .order_by('profile__role')
        )

        def fmt_period(item):
            period = item.get('period')
            if period is None:
                return ''
            if hasattr(period, 'strftime'):
                return period.strftime('%Y-%m-%d')
            return str(period)

        return Response({
            'kpis': {
                'total_users': total_users,
                'active_users': active_users,
                'frozen_accounts': frozen_accounts,
                'pending_orders': pending_orders,
                'total_recharge': total_recharge,
                'total_consumption': total_consumption,
                'recharge_count': recharge_count,
                'consumption_count': consumption_count,
            },
            'trends': {
                'recharge': [
                    {'period': fmt_period(item), 'amount': item['amount'] or 0, 'count': item['count']}
                    for item in recharge_trend
                ],
                'consumption': [
                    {'period': fmt_period(item), 'amount': item['amount'] or 0, 'count': item['count']}
                    for item in consumption_trend
                ],
                'user_growth': [
                    {'period': fmt_period(item), 'count': item['count']}
                    for item in user_growth_trend
                ],
            },
            'distributions': {
                'recharge_by_channel': recharge_by_channel,
                'consumption_by_category': consumption_by_category,
                'users_by_role': [
                    {'role': item['profile__role'] or 'unknown', 'count': item['count']}
                    for item in users_by_role
                ],
            },
        })


class DatasetQueryAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def _apply_filters(self, queryset, filters, date_field='created_at'):
        from django.utils import timezone
        from datetime import timedelta

        start_date = filters.get('start_date')
        end_date = filters.get('end_date')
        if start_date:
            queryset = queryset.filter(**{f'{date_field}__date__gte': start_date})
        if end_date:
            queryset = queryset.filter(**{f'{date_field}__date__lte': end_date})

        channel = filters.get('channel')
        if channel and hasattr(queryset.model, 'channel'):
            queryset = queryset.filter(channel=channel)

        category = filters.get('category')
        if category and hasattr(queryset.model, 'category'):
            queryset = queryset.filter(category=category)

        role = filters.get('role')
        if role:
            queryset = queryset.filter(profile__role=role)

        return queryset

    def _group_by_dimension(self, queryset, dimension):
        from django.db.models.functions import TruncDate, TruncWeek, TruncMonth

        dim_map = {
            'day': (TruncDate, 'period'),
            'week': (TruncWeek, 'period'),
            'month': (TruncMonth, 'period'),
            'channel': (None, 'channel'),
            'category': (None, 'category'),
            'role': (None, 'profile__role'),
        }
        return dim_map.get(dimension)

    def _aggregate_measures(self, queryset, measures, group_field, trunc_fn):
        from django.db.models import Avg

        annotations = {}
        if 'amount' in measures:
            amount_field = 'amount' if hasattr(queryset.model, 'amount') else 'cost_amount'
            annotations['amount'] = Sum(amount_field)
        if 'count' in measures:
            annotations['count'] = Count('id')
        if 'user_count' in measures:
            annotations['user_count'] = Count('user', distinct=True)
        if 'avg_amount' in measures:
            amount_field = 'amount' if hasattr(queryset.model, 'amount') else 'cost_amount'
            annotations['avg_amount'] = Avg(amount_field)

        if trunc_fn:
            queryset = queryset.annotate(**{group_field: trunc_fn(
                'created_at' if group_field == 'period' else 'date_joined'
            )})

        return list(queryset.values(group_field).annotate(**annotations).order_by(group_field))

    def post(self, request):
        serializer = DatasetQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        dataset = data['dataset']
        dimensions = data['dimensions'] or ['day']
        measures = data['measures'] or ['amount', 'count']
        filters = data['filters'] or {}

        if dataset == 'recharge':
            queryset = RechargeRecord.objects.all()
            queryset = self._apply_filters(queryset, filters)
        elif dataset == 'consumption':
            queryset = ConsumptionRecord.objects.all()
            queryset = self._apply_filters(queryset, filters)
        elif dataset == 'user_growth':
            queryset = User.objects.all()
            queryset = self._apply_filters(queryset, filters, date_field='date_joined')
        else:
            return Response({'detail': '未知数据集。'}, status=status.HTTP_400_BAD_REQUEST)

        dimension = dimensions[0] if dimensions else 'day'
        dim_info = self._group_by_dimension(queryset, dimension)
        if dim_info is None:
            return Response({'detail': f'不支持的维度：{dimension}'}, status=status.HTTP_400_BAD_REQUEST)

        trunc_fn, group_field = dim_info
        result = self._aggregate_measures(queryset, measures, group_field, trunc_fn)

        def fmt_row(row):
            out = {}
            for k, v in row.items():
                if k == 'period' and v is not None and hasattr(v, 'strftime'):
                    out[k] = v.strftime('%Y-%m-%d')
                elif k == 'profile__role':
                    out['role'] = v or 'unknown'
                else:
                    out[k] = v
            return out

        return Response({
            'dataset': dataset,
            'dimension': dimension,
            'measures': measures,
            'data': [fmt_row(r) for r in result],
        })


class SavedReportListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get(self, request):
        reports = SavedReport.objects.filter(user=request.user).order_by('-updated_at')
        return Response(SavedReportSerializer(reports, many=True).data)

    def post(self, request):
        serializer = SavedReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = serializer.save(user=request.user)
        return Response(SavedReportSerializer(report).data, status=status.HTTP_201_CREATED)


class SavedReportDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def _get_report(self, request, report_id):
        return SavedReport.objects.filter(id=report_id, user=request.user).first()

    def get(self, request, report_id):
        report = self._get_report(request, report_id)
        if not report:
            return Response({'detail': '报表不存在。'}, status=status.HTTP_404_NOT_FOUND)
        return Response(SavedReportSerializer(report).data)

    def put(self, request, report_id):
        report = self._get_report(request, report_id)
        if not report:
            return Response({'detail': '报表不存在。'}, status=status.HTTP_404_NOT_FOUND)
        serializer = SavedReportSerializer(report, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(SavedReportSerializer(report).data)

    def delete(self, request, report_id):
        report = self._get_report(request, report_id)
        if not report:
            return Response({'detail': '报表不存在。'}, status=status.HTTP_404_NOT_FOUND)
        report.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def post(self, request, report_id):
        report = self._get_report(request, report_id)
        if not report:
            return Response({'detail': '报表不存在。'}, status=status.HTTP_404_NOT_FOUND)

        view = DatasetQueryAPIView()
        request.data = {
            'dataset': report.dataset,
            'dimensions': report.dimensions,
            'measures': report.measures,
            'filters': report.filters,
        }
        return view.post(request)


class DashboardPreferenceAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def get(self, request):
        pref, _ = DashboardPreference.objects.get_or_create(user=request.user)
        return Response(DashboardPreferenceSerializer(pref).data)

    def put(self, request):
        pref, _ = DashboardPreference.objects.get_or_create(user=request.user)
        serializer = DashboardPreferenceSerializer(pref, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(DashboardPreferenceSerializer(pref).data)
