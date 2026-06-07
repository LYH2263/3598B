from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Profile
from accounts.permissions import IsAdminRole
from refund_invoice.models import (
    InvoiceRequest,
    InvoiceTitle,
    RefundRequest,
)
from refund_invoice.serializers import (
    InvoiceCreateSerializer,
    InvoiceProcessSerializer,
    InvoiceRequestSerializer,
    InvoiceTitleCreateSerializer,
    InvoiceTitleSerializer,
    InvoiceTitleUpdateSerializer,
    InvoiceVoidSerializer,
    InvoiceableRechargeSerializer,
    RefundCreateSerializer,
    RefundRequestSerializer,
    RefundReviewSerializer,
    RefundableRechargeSerializer,
)
from refund_invoice.services.invoice_service import InvoiceService
from refund_invoice.services.refund_service import RefundService


class RefundListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self, request):
        role = getattr(request.user.profile, 'role', Profile.ROLE_STUDENT)
        queryset = RefundRequest.objects.select_related(
            'user', 'reviewer', 'recharge_record'
        )
        if role != Profile.ROLE_ADMIN:
            queryset = queryset.filter(user=request.user)
        return queryset

    def get(self, request):
        queryset = self.get_queryset(request)
        status_filter = request.query_params.get('status', '').strip()
        user_id = request.query_params.get('user_id', '').strip()
        role = getattr(request.user.profile, 'role', Profile.ROLE_STUDENT)

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if user_id and role == Profile.ROLE_ADMIN:
            queryset = queryset.filter(user_id=user_id)

        return Response(RefundRequestSerializer(queryset[:200], many=True).data)

    def post(self, request):
        role = getattr(request.user.profile, 'role', Profile.ROLE_STUDENT)
        if role != Profile.ROLE_STUDENT:
            return Response({'detail': '仅学生可提交退费申请。'}, status=status.HTTP_403_FORBIDDEN)

        serializer = RefundCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        refund = serializer.save()
        return Response(RefundRequestSerializer(refund).data, status=status.HTTP_201_CREATED)


class RefundCancelAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, refund_id: int):
        refund = RefundService.cancel_refund_request(request.user, refund_id)
        return Response(RefundRequestSerializer(refund).data)


class RefundReviewAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def post(self, request, refund_id: int):
        refund = RefundRequest.objects.filter(id=refund_id).first()
        if not refund:
            return Response({'detail': '退费申请不存在。'}, status=status.HTTP_404_NOT_FOUND)

        serializer = RefundReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reviewed = RefundService.review_refund(
            refund=refund,
            action=serializer.validated_data['action'],
            reviewer=request.user,
            review_remark=serializer.validated_data.get('review_remark', ''),
        )
        return Response(RefundRequestSerializer(reviewed).data)


class RefundableRechargesAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        recharges = RefundService.get_refundable_recharges(request.user)
        return Response(RefundableRechargeSerializer(recharges, many=True).data)


class InvoiceTitleListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        titles = InvoiceTitle.objects.filter(user=request.user)
        return Response(InvoiceTitleSerializer(titles, many=True).data)

    def post(self, request):
        role = getattr(request.user.profile, 'role', Profile.ROLE_STUDENT)
        if role != Profile.ROLE_STUDENT:
            return Response({'detail': '仅学生可维护发票抬头。'}, status=status.HTTP_403_FORBIDDEN)

        serializer = InvoiceTitleCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        title = serializer.save()
        return Response(InvoiceTitleSerializer(title).data, status=status.HTTP_201_CREATED)


class InvoiceTitleDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _get_title(self, request, title_id: int):
        return InvoiceTitle.objects.filter(id=title_id, user=request.user).first()

    def put(self, request, title_id: int):
        title = self._get_title(request, title_id)
        if not title:
            return Response({'detail': '发票抬头不存在。'}, status=status.HTTP_404_NOT_FOUND)

        serializer = InvoiceTitleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated = InvoiceService.update_title(
            user=request.user,
            title_id=title_id,
            **{k: v for k, v in serializer.validated_data.items() if v is not None},
        )
        return Response(InvoiceTitleSerializer(updated).data)

    def delete(self, request, title_id: int):
        InvoiceService.delete_title(request.user, title_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class InvoiceTitleSetDefaultAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, title_id: int):
        title = InvoiceService.set_default_title(request.user, title_id)
        return Response(InvoiceTitleSerializer(title).data)


class InvoiceRequestListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self, request):
        role = getattr(request.user.profile, 'role', Profile.ROLE_STUDENT)
        queryset = InvoiceRequest.objects.select_related(
            'user', 'reviewer', 'title'
        ).prefetch_related('items', 'items__recharge_record')
        if role != Profile.ROLE_ADMIN:
            queryset = queryset.filter(user=request.user)
        return queryset

    def get(self, request):
        queryset = self.get_queryset(request)
        status_filter = request.query_params.get('status', '').strip()
        user_id = request.query_params.get('user_id', '').strip()
        role = getattr(request.user.profile, 'role', Profile.ROLE_STUDENT)

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if user_id and role == Profile.ROLE_ADMIN:
            queryset = queryset.filter(user_id=user_id)

        return Response(InvoiceRequestSerializer(queryset[:200], many=True).data)

    def post(self, request):
        role = getattr(request.user.profile, 'role', Profile.ROLE_STUDENT)
        if role != Profile.ROLE_STUDENT:
            return Response({'detail': '仅学生可提交开票申请。'}, status=status.HTTP_403_FORBIDDEN)

        serializer = InvoiceCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        invoice = serializer.save()
        invoice = (
            InvoiceRequest.objects.select_related('user', 'reviewer', 'title')
            .prefetch_related('items', 'items__recharge_record')
            .get(id=invoice.id)
        )
        return Response(InvoiceRequestSerializer(invoice).data, status=status.HTTP_201_CREATED)


class InvoiceRequestDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk: int):
        role = getattr(request.user.profile, 'role', Profile.ROLE_STUDENT)
        invoice = (
            InvoiceRequest.objects.select_related('user', 'reviewer', 'title')
            .prefetch_related('items', 'items__recharge_record')
            .filter(pk=pk)
            .first()
        )
        if not invoice:
            return Response({'detail': '开票申请不存在。'}, status=status.HTTP_404_NOT_FOUND)
        if role != Profile.ROLE_ADMIN and invoice.user_id != request.user.id:
            return Response({'detail': '无权查看此开票申请。'}, status=status.HTTP_403_FORBIDDEN)

        return Response(InvoiceRequestSerializer(invoice).data)


class InvoiceProcessAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def post(self, request, pk: int):
        invoice = InvoiceRequest.objects.filter(pk=pk).first()
        if not invoice:
            return Response({'detail': '开票申请不存在。'}, status=status.HTTP_404_NOT_FOUND)

        serializer = InvoiceProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        processed = InvoiceService.process_invoice(
            invoice=invoice,
            action=data['action'],
            reviewer=request.user,
            invoice_number=data.get('invoice_number', ''),
            download_url=data.get('download_url', ''),
            review_remark=data.get('review_remark', ''),
        )
        processed = (
            InvoiceRequest.objects.select_related('user', 'reviewer', 'title')
            .prefetch_related('items', 'items__recharge_record')
            .get(id=processed.id)
        )
        return Response(InvoiceRequestSerializer(processed).data)


class InvoiceVoidAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

    def post(self, request, pk: int):
        invoice = InvoiceRequest.objects.filter(pk=pk).first()
        if not invoice:
            return Response({'detail': '开票申请不存在。'}, status=status.HTTP_404_NOT_FOUND)

        serializer = InvoiceVoidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        voided = InvoiceService.void_invoice(
            invoice=invoice,
            reviewer=request.user,
            review_remark=serializer.validated_data.get('review_remark', ''),
        )
        voided = (
            InvoiceRequest.objects.select_related('user', 'reviewer', 'title')
            .prefetch_related('items', 'items__recharge_record')
            .get(id=voided.id)
        )
        return Response(InvoiceRequestSerializer(voided).data)


class InvoiceableRechargesAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        recharges = InvoiceService.get_invoiceable_recharges(request.user)
        return Response(InvoiceableRechargeSerializer(recharges, many=True).data)
