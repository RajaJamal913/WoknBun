from decimal import Decimal
from rest_framework import serializers
from .models import Order, OrderItem

DELIVERY_CHARGES = Decimal("250.00")
TAX_RATE = Decimal("0.16")


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["item_name", "size_label", "unit_price", "quantity"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            "id", "full_name", "mobile_number", "email", "alt_phone",
            "address_line", "special_instructions", "payment_method",
            "subtotal", "delivery_charges", "tax_amount", "grand_total",
            "status", "created_at", "items",
        ]
        read_only_fields = ["id", "subtotal", "delivery_charges", "tax_amount", "grand_total", "status", "created_at"]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        if not items_data:
            raise serializers.ValidationError("Cart is empty.")

        subtotal = sum(i["unit_price"] * i["quantity"] for i in items_data)
        tax_amount = (subtotal * TAX_RATE).quantize(Decimal("0.01"))
        grand_total = subtotal + DELIVERY_CHARGES + tax_amount

        order = Order.objects.create(
            subtotal=subtotal,
            delivery_charges=DELIVERY_CHARGES,
            tax_amount=tax_amount,
            grand_total=grand_total,
            **validated_data,
        )
        for item in items_data:
            line_total = item["unit_price"] * item["quantity"]
            OrderItem.objects.create(order=order, line_total=line_total, **item)
        return order
