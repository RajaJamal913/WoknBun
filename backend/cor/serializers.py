from django.conf import settings
from django.db import transaction
from rest_framework import serializers

from decimal import Decimal

from accounts.models import Customer
from accounts.phone import normalize_phone
from accounts.services import find_or_create_customer
from pos.models import Shift
from pos.permissions import is_manager, owns_shift
from pos.serializers import calc_delivery

from .models import Category, Deal, MenuItem, MenuItemPrice, Order, OrderItem, Refund, Settlement
from .pricing import OrderLineSerializer, build_lines, calc_tax, money


class MenuItemPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItemPrice
        fields = ["id", "label", "price"]


class MenuItemSerializer(serializers.ModelSerializer):
    prices = MenuItemPriceSerializer(many=True, read_only=True)
    category = serializers.SlugRelatedField(slug_field="slug", read_only=True)

    class Meta:
        model = MenuItem
        fields = ["id", "category", "name", "description", "note", "image_url", "badge", "prices"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "order"]


class DealSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deal
        fields = ["id", "name", "description", "price", "badge", "image_url"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderLineSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            "id", "full_name", "mobile_number", "email", "alt_phone",
            "address_line", "special_instructions", "payment_method",
            "subtotal", "delivery_charges", "tax_amount", "grand_total",
            "status", "created_at", "items",
        ]
        read_only_fields = ["id", "subtotal", "delivery_charges", "tax_amount", "grand_total", "status", "created_at"]
        # The model lets these be blank (counter sales have none); a website order may not.
        extra_kwargs = {
            "full_name": {"required": True, "allow_blank": False},
            "mobile_number": {"required": True, "allow_blank": False},
            "address_line": {"required": True, "allow_blank": False},
        }

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Cart is empty.")
        return value

    def validate_mobile_number(self, value):
        if not normalize_phone(value):
            raise serializers.ValidationError("Enter a valid mobile number, e.g. 0300 1234567.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        lines = build_lines(validated_data.pop("items"))
        subtotal = sum((l["line_total"] for l in lines), money(0))
        tax_amount = calc_tax(subtotal)
        delivery = money(settings.DELIVERY_CHARGES)
        grand_total = subtotal + delivery + tax_amount

        user = getattr(self.context.get("request"), "user", None)
        account = user if isinstance(user, Customer) else None
        customer = account or find_or_create_customer(
            validated_data.get("full_name"), validated_data.get("mobile_number"),
            validated_data.get("email", ""), validated_data.get("alt_phone", ""))

        order = Order.objects.create(
            customer=customer, placed_by_account=account is not None,
            subtotal=subtotal, delivery_charges=delivery,
            tax_amount=tax_amount, grand_total=grand_total, **validated_data,
        )
        OrderItem.objects.bulk_create([OrderItem(order=order, **l) for l in lines])
        return order


class PosOrderSerializer(serializers.ModelSerializer):
    """An order rung up at the POS terminal for this restaurant (same payload the terminal sends for its own menu)."""
    items = OrderLineSerializer(many=True)
    customer_info = serializers.SerializerMethodField()
    payment = serializers.SerializerMethodField()
    client_order_id = serializers.UUIDField(validators=[])  # a retried sync is valid - create() returns the existing order
    shift = serializers.PrimaryKeyRelatedField(queryset=Shift.objects.all())
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all(), required=False, allow_null=True)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, default=Decimal("0"))
    delivery_distance_km = serializers.DecimalField(
        max_digits=4, decimal_places=1, min_value=Decimal("0"), max_value=Decimal("100"), required=False, write_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "client_order_id", "shift", "order_type", "table_label", "status",
            "subtotal", "discount_amount", "tax_amount", "delivery_charges", "grand_total",
            "customer", "customer_info", "created_at", "settled_at", "cancel_reason", "cancelled_at",
            "payment", "items", "delivery_distance_km",
        ]
        read_only_fields = [
            "id", "status", "subtotal", "tax_amount", "delivery_charges", "grand_total",
            "created_at", "settled_at", "cancel_reason", "cancelled_at",
        ]

    def get_customer_info(self, obj):
        c = obj.customer
        return {"id": c.id, "full_name": c.full_name} if c else None

    def get_payment(self, obj):
        st = Settlement.objects.filter(order=obj).first()
        return SettlementSerializer(st).data if st else None

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("An order needs at least one item.")
        return value

    def validate(self, attrs):
        order_type = attrs.get("order_type")
        if order_type not in ("counter", "dine_in", "takeaway"):
            raise serializers.ValidationError({"order_type": "Choose counter, dine in or takeaway."})
        table = (attrs.get("table_label") or "").strip()
        if order_type == "dine_in" and not table:
            raise serializers.ValidationError({"table_label": "Enter the table for a dine-in order."})
        attrs["table_label"] = table if order_type == "dine_in" else ""
        if attrs.get("delivery_distance_km") and order_type != "takeaway":
            raise serializers.ValidationError({"delivery_distance_km": "Delivery distance only applies to takeaway orders."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = self.context["request"].user

        existing = Order.objects.filter(client_order_id=validated_data["client_order_id"]).first()
        if existing:  # the terminal retried a sync that had already gone through
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

        delivery = calc_delivery(validated_data.pop("delivery_distance_km", None))
        tax_amount = calc_tax(subtotal - discount)
        grand_total = subtotal - discount + tax_amount + delivery

        order = Order.objects.create(
            source="pos", status="open", payment_method="cod",
            subtotal=subtotal, discount_amount=discount, tax_amount=tax_amount,
            delivery_charges=delivery, grand_total=grand_total, **validated_data,
        )
        OrderItem.objects.bulk_create([OrderItem(order=order, **l) for l in lines])
        return order


class OrderStatusSerializer(serializers.ModelSerializer):
    """Staff-only: move a WEBSITE order along (and say why if it is cancelled)."""
    class Meta:
        model = Order
        fields = ["status", "cancel_reason"]

    def validate(self, attrs):
        # POS sales have their own flow (settle / refund / cancel on the terminal).
        if self.instance is not None and self.instance.source == "pos":
            raise serializers.ValidationError("This is a POS sale - settle, refund or cancel it on the POS terminal.")
        if attrs.get("status") not in (None, *Order.WEB_STATUSES):
            raise serializers.ValidationError({"status": "Not a website order status."})
        return attrs


class SettlementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settlement
        fields = ["id", "order", "cashier", "payment_method", "amount_tendered", "change_due", "settled_at"]
        read_only_fields = fields


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = ["id", "order", "cashier", "amount", "reason", "refunded_at"]
        read_only_fields = fields


class SettleOrderSerializer(serializers.Serializer):
    payment_method = serializers.ChoiceField(choices=Settlement.PAYMENT_CHOICES)
    amount_tendered = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False)

    def validate(self, attrs):
        if attrs["payment_method"] == "cash" and attrs.get("amount_tendered") is None:
            raise serializers.ValidationError({"amount_tendered": "Enter the cash received."})
        return attrs


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)
