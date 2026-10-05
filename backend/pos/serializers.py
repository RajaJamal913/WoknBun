from decimal import Decimal

from django.db import IntegrityError, transaction
from rest_framework import serializers

from menu.pricing import OrderLineSerializer, build_lines, calc_tax, money
from .models import Shift, Order, OrderItem, Settlement, Refund
from .permissions import is_manager, owns_shift


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
    discount_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=Decimal("0")
    )

    class Meta:
        model = Order
        fields = [
            "id", "client_order_id", "shift", "order_type", "table_label", "status",
            "subtotal", "discount_amount", "tax_amount", "grand_total",
            "created_at", "settled_at", "items",
        ]
        # Totals are computed by the server - never accepted from a client.
        read_only_fields = [
            "id", "status", "subtotal", "tax_amount", "grand_total",
            "created_at", "settled_at",
        ]

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("An order needs at least one item.")
        return value

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

        tax_amount = calc_tax(subtotal - discount)
        grand_total = subtotal - discount + tax_amount

        try:
            with transaction.atomic():
                order = Order.objects.create(
                    subtotal=subtotal,
                    discount_amount=discount,
                    tax_amount=tax_amount,
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


class RefundOrderSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = ["id", "order", "cashier", "amount", "reason", "refunded_at"]
        read_only_fields = fields
