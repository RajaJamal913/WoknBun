from django.db import transaction
from rest_framework import serializers

from django.conf import settings
from menu.pricing import OrderLineSerializer, build_lines, calc_tax, money
from .models import Order, OrderItem


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

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Cart is empty.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        lines = build_lines(validated_data.pop("items"))

        subtotal = sum((l["line_total"] for l in lines), money(0))
        tax_amount = calc_tax(subtotal)
        delivery = money(settings.DELIVERY_CHARGES)
        grand_total = subtotal + delivery + tax_amount

        order = Order.objects.create(
            subtotal=subtotal,
            delivery_charges=delivery,
            tax_amount=tax_amount,
            grand_total=grand_total,
            **validated_data,
        )
        OrderItem.objects.bulk_create([OrderItem(order=order, **l) for l in lines])
        return order
