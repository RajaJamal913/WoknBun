from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import IntegrityError, transaction
from rest_framework import serializers

from accounts.models import Customer
from menu.pricing import OrderLineSerializer, build_lines, calc_tax, money
from .models import Shift, Order, OrderItem, Settlement, Refund
from .permissions import is_manager, owns_shift

# Takeaway delivery rate in Rs. per km. Keep in step with DELIVERY_RATE_PER_KM in the POS
# terminal (renderer/delivery.js) so the bill on screen matches the saved order.
DELIVERY_RATE_PER_KM = Decimal(str(getattr(settings, "DELIVERY_RATE_PER_KM", 15)))


def calc_delivery(km):
    """Takeaway delivery charge: km x rate, in whole rupees, rounding half up (same rule as the POS)."""
    if not km:
        return money(0)
    return money((Decimal(km) * DELIVERY_RATE_PER_KM).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class ShiftSerializer(serializers.ModelSerializer):
    cashier_name = serializers.SerializerMethodField()

    class Meta:
        model = Shift
        fields = ["id", "cashier", "cashier_name", "status", "opening_cash", "closing_cash", "opened_at", "closed_at"]
        read_only_fields = ["id", "cashier", "cashier_name", "status", "opened_at", "closed_at"]

    def get_cashier_name(self, obj):
        return obj.cashier.get_full_name() or obj.cashier.get_username()


class OpenShiftSerializer(serializers.Serializer):
    opening_cash = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=Decimal("0"))


class CloseShiftSerializer(serializers.Serializer):
    closing_cash = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0"))


class OrderSerializer(serializers.ModelSerializer):
    items = OrderLineSerializer(many=True)
    # A duplicate client_order_id is an expected, valid case (a retried sync),
    # not a validation error - create() returns the existing order for it.
    client_order_id = serializers.UUIDField(validators=[])
    online = serializers.SerializerMethodField()
    # Optional: the customer the cashier attached at the till (the terminal sends their id).
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all(), required=False, allow_null=True)
    customer_info = serializers.SerializerMethodField()
    discount_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=Decimal("0")
    )
    # Takeaway only: how far the order is going. The server turns it into delivery_charges itself
    # (the amount is never accepted from a client). Not stored - it is only an input to the charge.
    delivery_distance_km = serializers.DecimalField(
        max_digits=4, decimal_places=1, min_value=Decimal("0"), max_value=Decimal("100"),
        required=False, write_only=True,
    )

    class Meta:
        model = Order
        fields = [
            "id", "client_order_id", "shift", "order_type", "table_label", "status", "cancel_reason", "cancelled_at",
            "subtotal", "discount_amount", "tax_amount", "delivery_charges", "grand_total",
            "customer", "customer_info", "online", "created_at", "settled_at", "items",
            "delivery_distance_km",
        ]
        # Totals are computed by the server - never accepted from a client.
        read_only_fields = [
            "id", "status", "subtotal", "tax_amount", "delivery_charges", "grand_total",
            "cancel_reason", "cancelled_at", "created_at", "settled_at",
        ]

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("An order needs at least one item.")
        return value

    def get_customer_info(self, obj):
        """Just enough for receipts and history; the full profile lives on the Customers screen."""
        c = obj.customer
        return {"id": c.id, "full_name": c.full_name} if c else None

    def get_online(self, obj):
        """Customer details when this sale came from the website (else None)."""
        w = obj.online_order
        if w is None:
            return None
        return {"id": w.id, "full_name": w.full_name, "mobile_number": w.mobile_number,
                "address_line": w.address_line, "special_instructions": w.special_instructions}

    def validate(self, attrs):
        if attrs.get("order_type") == "online":
            raise serializers.ValidationError({"order_type": "Online orders come from the website - accept them in Online Orders."})
        # The kitchen and waiters find a dine-in order by its table.
        table = (attrs.get("table_label") or "").strip()
        if attrs.get("order_type") == "dine_in" and not table:
            raise serializers.ValidationError({"table_label": "Enter the table for a dine-in order."})
        attrs["table_label"] = table if attrs.get("order_type") == "dine_in" else ""
        # Delivery is a takeaway thing; a distance on any other order type is a mistake, not something to ignore.
        if attrs.get("delivery_distance_km") and attrs.get("order_type") != "takeaway":
            raise serializers.ValidationError({"delivery_distance_km": "Delivery distance only applies to takeaway orders."})
        return attrs

    def _user(self):
        return self.context["request"].user

    def create(self, validated_data):
        user = self._user()

        # Idempotent: if the terminal retries a sync (e.g. after a dropped
        # connection), the same client_order_id must never create a duplicate.
        existing = self._existing(validated_data["client_order_id"], user)
        if existing:
            return existing

        shift = validated_data["shift"]
        if not owns_shift(user, shift):
            raise serializers.ValidationError({"shift": "This shift belongs to another cashier."})
        if shift.status != "open":
            raise serializers.ValidationError({"shift": "Cannot punch an order onto a closed shift."})

        lines = build_lines(validated_data.pop("items"))
        subtotal = sum((l["line_total"] for l in lines), money(0))

        discount = money(validated_data.pop("discount_amount", 0))
        if discount > subtotal:
            raise serializers.ValidationError({"discount_amount": "Discount cannot exceed the order subtotal."})
        if discount > 0 and not is_manager(user):
            raise serializers.ValidationError({"discount_amount": "Only a manager can apply a discount."})

        # Delivery is added after tax: it is not taxed and not discounted.
        # (Pop the distance now - Order has no such column, so it must not reach Order.objects.create.)
        delivery = calc_delivery(validated_data.pop("delivery_distance_km", None))
        tax_amount = calc_tax(subtotal - discount)
        grand_total = subtotal - discount + tax_amount + delivery

        try:
            with transaction.atomic():
                order = Order.objects.create(
                    subtotal=subtotal,
                    discount_amount=discount,
                    tax_amount=tax_amount,
                    delivery_charges=delivery,
                    grand_total=grand_total,
                    **validated_data,
                )
                OrderItem.objects.bulk_create([OrderItem(order=order, **l) for l in lines])
        except IntegrityError:
            # Two retries raced; the other one won - hand back its order.
            existing = self._existing(validated_data["client_order_id"], user)
            if existing:
                return existing
            raise
        return order

    def _existing(self, client_order_id, user):
        existing = Order.objects.select_related("shift").filter(client_order_id=client_order_id).first()
        if existing and not owns_shift(user, existing.shift):
            raise serializers.ValidationError({"client_order_id": "This order id belongs to another cashier."})
        return existing


class SettleOrderSerializer(serializers.Serializer):
    payment_method = serializers.ChoiceField(choices=Settlement.PAYMENT_CHOICES)
    amount_tendered = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False)

    def validate(self, attrs):
        if attrs["payment_method"] == "cash" and attrs.get("amount_tendered") is None:
            raise serializers.ValidationError({"amount_tendered": "Enter the cash received."})
        return attrs


class SettlementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settlement
        fields = ["id", "order", "cashier", "payment_method", "amount_tendered", "change_due", "settled_at"]
        read_only_fields = fields


class CancelOrderSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)


class RefundOrderSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = ["id", "order", "cashier", "amount", "reason", "refunded_at"]
        read_only_fields = fields