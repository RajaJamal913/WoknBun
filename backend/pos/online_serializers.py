from rest_framework import serializers

from orders.models import Order as OnlineOrder, OrderItem as OnlineOrderItem


class OnlineOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnlineOrderItem
        fields = ["item_name", "size_label", "quantity", "unit_price", "line_total"]


class OnlineOrderSerializer(serializers.ModelSerializer):
    items = OnlineOrderItemSerializer(many=True, read_only=True)
    accepted_by_name = serializers.SerializerMethodField()
    pos_order_id = serializers.SerializerMethodField()

    class Meta:
        model = OnlineOrder
        fields = [
            "id", "full_name", "mobile_number", "alt_phone", "email", "address_line", "special_instructions",
            "payment_method", "subtotal", "delivery_charges", "tax_amount", "grand_total",
            "status", "cancel_reason", "created_at", "status_changed_at",
            "accepted_by_name", "pos_order_id", "items",
        ]
        read_only_fields = fields

    def get_accepted_by_name(self, obj):
        u = obj.accepted_by
        return (u.get_full_name() or u.get_username()) if u else ""

    def get_pos_order_id(self, obj):
        sale = getattr(obj, "pos_order", None)  # None when the order hasn't been accepted yet
        return sale.id if sale else None