from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.utils import timezone
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.authentication import OptionalCustomerAuthentication
from pos.permissions import CanRefund, CanViewReports, IsCashierOrAbove, IsPOSStaff, owns_shift, staff_role
from pos.report_views import _date_param, _range

from . import reports
from .models import Category, Deal, MenuItem, Order, Refund, Settlement
from .pricing import money
from .serializers import (
    CategorySerializer, DealSerializer, MenuItemSerializer,
    OrderSerializer, OrderStatusSerializer, PosOrderSerializer, ReasonSerializer,
    RefundSerializer, SettleOrderSerializer, SettlementSerializer,
)


class IsStaff(permissions.BasePermission):
    """Staff users only (a signed-in customer is not staff)."""
    def has_permission(self, request, view):
        return bool(request.user and getattr(request.user, "is_staff", False))


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class MenuItemViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = MenuItem.objects.filter(is_active=True).select_related("category").prefetch_related("prices")
    serializer_class = MenuItemSerializer


class DealViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = Deal.objects.filter(is_active=True)
    serializer_class = DealSerializer


class OrderViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                   mixins.RetrieveModelMixin, mixins.UpdateModelMixin,
                   viewsets.GenericViewSet):
    """
    POST   /orders/        public - customers place cash-on-delivery orders (no account needed)
    GET    /orders/        staff only
    GET    /orders/<id>/   staff only
    PATCH  /orders/<id>/   staff only - change status
    """
    queryset = Order.objects.all().prefetch_related("items")
    http_method_names = ["get", "post", "patch", "head", "options"]
    # A customer token is optional on the public POST; staff use JWT/session for the rest.
    authentication_classes = [
        OptionalCustomerAuthentication,
        JWTAuthentication,
        SessionAuthentication,
    ]

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        return [IsStaff()]

    def get_throttles(self):
        if self.action == "create":
            throttle = ScopedRateThrottle()
            self.throttle_scope = "order_create"
            return [throttle]
        return []

    def get_serializer_class(self):
        return OrderStatusSerializer if self.action == "partial_update" else OrderSerializer

    def perform_update(self, serializer):
        serializer.save(status_changed_at=timezone.now())

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response(OrderSerializer(self.get_object(), context={"request": request}).data)


def _bad_request(message):
    return Response({"detail": message}, status=status.HTTP_400_BAD_REQUEST)


def _locked_pos_order(order_id):
    """Row-locked fetch so a double-click or a second terminal can't act on the same order twice."""
    try:
        return Order.objects.select_for_update().select_related("shift").get(id=order_id, source="pos")
    except Order.DoesNotExist:
        raise Http404("Order not found.")


class PosOrderListCreateView(generics.ListCreateAPIView):
    """
    GET  /pos-orders/?shift=<id>  the order history for a shift (cashiers see only their own shifts)
    POST /pos-orders/             the POS terminal records a sale for this restaurant
    """
    serializer_class = PosOrderSerializer

    def get_permissions(self):
        return [IsPOSStaff()] if self.request.method == "GET" else [IsCashierOrAbove()]

    def get_serializer_context(self):
        # The cashier already served what was on their screen; an item hidden since must not lose a sale.
        return {**super().get_serializer_context(), "allow_inactive_menu": True}

    def get_queryset(self):
        qs = Order.objects.filter(source="pos").select_related("shift", "customer").prefetch_related("items")
        if staff_role(self.request.user) == "cashier":
            qs = qs.filter(shift__cashier=self.request.user)
        shift_id = self.request.query_params.get("shift")
        if shift_id and shift_id.isdigit():
            qs = qs.filter(shift_id=shift_id)
        return qs


class PosSettleOrderView(APIView):
    permission_classes = [IsCashierOrAbove]

    def post(self, request, order_id):
        serializer = SettleOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        method = serializer.validated_data["payment_method"]

        with transaction.atomic():
            order = _locked_pos_order(order_id)
            if not owns_shift(request.user, order.shift):
                raise PermissionDenied("This order belongs to another cashier's shift.")
            if order.status != "open":
                return _bad_request(f"Cannot settle an order with status '{order.status}'.")

            if method == "card":
                tendered, change = order.grand_total, money(0)
            else:
                tendered = money(serializer.validated_data["amount_tendered"])
                if tendered < order.grand_total:
                    return _bad_request("Amount tendered is less than the order total.")
                change = tendered - order.grand_total

            settlement = Settlement.objects.create(
                order=order, cashier=request.user, payment_method=method,
                amount_tendered=tendered, change_due=change,
            )
            order.status = "settled"
            order.settled_at = timezone.now()
            order.save(update_fields=["status", "settled_at"])

        return Response({
            "order": PosOrderSerializer(order, context={"request": request}).data,
            "settlement": SettlementSerializer(settlement).data,
        })


class PosRefundOrderView(APIView):
    permission_classes = [CanRefund]

    def post(self, request, order_id):
        serializer = ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            order = _locked_pos_order(order_id)
            if order.status != "settled":
                return _bad_request("Only a settled order can be refunded.")
            refund = Refund.objects.create(
                order=order, cashier=request.user, amount=order.grand_total,
                reason=serializer.validated_data.get("reason", ""),
            )
            order.status = "refunded"
            order.save(update_fields=["status"])
        return Response({
            "order": PosOrderSerializer(order, context={"request": request}).data,
            "refund": RefundSerializer(refund).data,
        })


class PosCancelOrderView(APIView):
    """Cancel an unpaid order (wrong entry, customer left). Paid orders use Refund instead."""
    permission_classes = [IsCashierOrAbove]

    def post(self, request, order_id):
        serializer = ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            order = _locked_pos_order(order_id)
            if not owns_shift(request.user, order.shift):
                raise PermissionDenied("This order belongs to another cashier's shift.")
            if order.status != "open":
                return _bad_request("Only an unpaid (open) order can be cancelled.")
            order.status = "cancelled"
            order.cancel_reason = serializer.validated_data.get("reason", "").strip()
            order.cancelled_at = timezone.now()
            order.save(update_fields=["status", "cancel_reason", "cancelled_at"])
        return Response(PosOrderSerializer(order, context={"request": request}).data)


# ---- reports (managers; same roles as the main POS reports) ----
class SalesSummaryView(APIView):
    permission_classes = [CanViewReports]

    def get(self, request):
        return Response(reports.sales_summary(*_range(request)))


class SalesReportView(APIView):
    permission_classes = [CanViewReports]

    def get(self, request):
        return Response(reports.item_sales(*_range(request)))


class HourlySalesView(APIView):
    permission_classes = [CanViewReports]

    def get(self, request):
        return Response(reports.hourly_sales(_date_param(request, "date", timezone.localdate())))


class CancellationReportView(APIView):
    permission_classes = [CanViewReports]

    def get(self, request):
        return Response(reports.cancellations(*_range(request)))


class ConfigView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({
            "restaurant": "Shangyaki",
            "tax_rate": str(settings.TAX_RATE),
            "delivery_charges": str(settings.DELIVERY_CHARGES),
        })
