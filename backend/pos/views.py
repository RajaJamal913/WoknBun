from django.db import IntegrityError, transaction
from django.http import Http404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from menu.pricing import money
from .models import Shift, Order, Settlement, Refund
from .permissions import (
    CanRefund, IsCashierOrAbove, IsPOSStaff, is_manager, owns_shift, staff_role,
)
from .serializers import (
    CancelOrderSerializer, CloseShiftSerializer, OpenShiftSerializer, OrderSerializer, RefundOrderSerializer,
    RefundSerializer, SettleOrderSerializer, SettlementSerializer, ShiftSerializer,
)


def _locked_order(order_id):
    """Fetch an order row-locked (inside a transaction) so double-clicks and
    two terminals can't act on the same order at once."""
    try:
        return Order.objects.select_for_update().select_related("shift").get(id=order_id)
    except Order.DoesNotExist:
        raise Http404("Order not found.")


def _bad_request(message):
    return Response({"detail": message}, status=status.HTTP_400_BAD_REQUEST)


class OpenShiftView(APIView):
    permission_classes = [IsCashierOrAbove]

    def post(self, request):
        serializer = OpenShiftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                if Shift.objects.filter(cashier=request.user, status="open").exists():
                    return _bad_request("You already have an open shift.")
                shift = Shift.objects.create(
                    cashier=request.user, opening_cash=serializer.validated_data["opening_cash"]
                )
        except IntegrityError:  # lost a race with another open request
            return _bad_request("You already have an open shift.")
        return Response(ShiftSerializer(shift).data, status=status.HTTP_201_CREATED)


class CloseShiftView(APIView):
    permission_classes = [IsCashierOrAbove]

    def post(self, request, shift_id):
        serializer = CloseShiftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            try:
                shift = Shift.objects.select_for_update().get(id=shift_id, cashier=request.user, status="open")
            except Shift.DoesNotExist:
                return Response({"detail": "No matching open shift found."}, status=status.HTTP_404_NOT_FOUND)

            if shift.orders.filter(status="open").exists():
                return _bad_request("Cannot close shift: there are still unsettled orders on it.")

            shift.status = "closed"
            shift.closing_cash = serializer.validated_data["closing_cash"]
            shift.closed_at = timezone.now()
            shift.save()
        return Response(ShiftSerializer(shift).data)


class CurrentShiftView(APIView):
    """Lets the terminal resume the cashier's open shift after a restart or re-login."""
    permission_classes = [IsPOSStaff]

    def get(self, request):
        shift = Shift.objects.filter(cashier=request.user, status="open").first()
        if not shift:
            return Response({"detail": "No open shift."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ShiftSerializer(shift).data)


class OrderListCreateView(generics.ListCreateAPIView):
    serializer_class = OrderSerializer

    def get_permissions(self):
        # Anyone on staff can read; only roles that take money can punch orders.
        return [IsPOSStaff()] if self.request.method == "GET" else [IsCashierOrAbove()]

    def get_queryset(self):
        qs = Order.objects.all().select_related("shift", "online_order").prefetch_related("items")
        # Cashiers see only their own shifts' orders; managers/admin/kitchen see all.
        if staff_role(self.request.user) == "cashier":
            qs = qs.filter(shift__cashier=self.request.user)
        shift_id = self.request.query_params.get("shift")
        if shift_id and shift_id.isdigit():
            qs = qs.filter(shift_id=shift_id)
        return qs


class SettleOrderView(APIView):
    permission_classes = [IsCashierOrAbove]

    def post(self, request, order_id):
        serializer = SettleOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment_method = serializer.validated_data["payment_method"]

        with transaction.atomic():
            order = _locked_order(order_id)
            if not owns_shift(request.user, order.shift):
                raise PermissionDenied("This order belongs to another cashier's shift.")
            if order.online_order_id:
                return _bad_request("This is a website order - use Online Orders to deliver or cancel it.")
            if order.status != "open":
                return _bad_request(f"Cannot settle an order with status '{order.status}'.")

            if payment_method == "card":
                # Card is charged for exactly the total; there is no change.
                amount_tendered = order.grand_total
                change_due = money(0)
            else:
                amount_tendered = money(serializer.validated_data["amount_tendered"])
                if amount_tendered < order.grand_total:
                    return _bad_request("Amount tendered is less than the order total.")
                change_due = amount_tendered - order.grand_total

            settlement = Settlement.objects.create(
                order=order, cashier=request.user, payment_method=payment_method,
                amount_tendered=amount_tendered, change_due=change_due,
            )
            order.status = "settled"
            order.settled_at = timezone.now()
            order.save(update_fields=["status", "settled_at"])

        return Response(
            {"order": OrderSerializer(order).data, "settlement": SettlementSerializer(settlement).data},
            status=status.HTTP_200_OK,
        )


class RefundOrderView(APIView):
    permission_classes = [CanRefund]

    def post(self, request, order_id):
        serializer = RefundOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            order = _locked_order(order_id)
            if order.status != "settled":
                return _bad_request("Only a settled order can be refunded.")

            refund = Refund.objects.create(
                order=order, cashier=request.user, amount=order.grand_total,
                reason=serializer.validated_data.get("reason", ""),
            )
            order.status = "refunded"
            order.save(update_fields=["status"])

        return Response(
            {"order": OrderSerializer(order).data, "refund": RefundSerializer(refund).data},
            status=status.HTTP_200_OK,
        )


class CancelOrderView(APIView):
    """Cancel an unpaid order (wrong entry, customer left). Paid orders use Refund instead."""
    permission_classes = [IsCashierOrAbove]

    def post(self, request, order_id):
        serializer = CancelOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            order = _locked_order(order_id)
            if not owns_shift(request.user, order.shift):
                raise PermissionDenied("This order belongs to another cashier's shift.")
            if order.online_order_id:
                return _bad_request("This is a website order - use Online Orders to deliver or cancel it.")
            if order.status != "open":
                return _bad_request("Only an unpaid (open) order can be cancelled.")
            order.status = "cancelled"
            order.cancel_reason = serializer.validated_data.get("reason", "").strip()
            order.cancelled_at = timezone.now()
            order.save(update_fields=["status", "cancel_reason", "cancelled_at"])
        return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)