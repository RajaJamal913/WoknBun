from django.db.models import Q
from rest_framework import serializers

from pos.models import Order as PosSale
from orders.models import Order as OnlineOrder, OrderItem as OnlineOrderItem


class OnlineOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnlineOrderItem
        fields = ["item_name", "size_label", "quantity", "unit_price", "line_total"]


class OnlineOrderSerializer(serializers.ModelSerializer):
    items = OnlineOrderItemSerializer(many=True, read_only=True)
    accepted_by_name = serializers.SerializerMethodField()
    pos_order_id = serializers.SerializerMethodField()
    customer_id = serializers.IntegerField(read_only=True)   # lets the POS open the customer's profile
    customer_orders = serializers.SerializerMethodField()    # how many paid orders they have had before

    class Meta:
        model = OnlineOrder
        fields = [
            "id", "full_name", "mobile_number", "alt_phone", "email", "address_line", "special_instructions",
            "payment_method", "subtotal", "delivery_charges", "tax_amount", "grand_total",
            "status", "cancel_reason", "created_at", "status_changed_at",
            "accepted_by_name", "pos_order_id", "customer_id", "customer_orders", "items",
        ]
        read_only_fields = fields

    def get_accepted_by_name(self, obj):
        u = obj.accepted_by
        return (u.get_full_name() or u.get_username()) if u else ""

    def get_pos_order_id(self, obj):
        sale = getattr(obj, "pos_order", None)  # None when the order hasn't been accepted yet
        return sale.id if sale else None

    def get_customer_orders(self, obj):
        """Settled sales this customer has had (counter or website). 0 = a new customer."""
        if not obj.customer_id:
            return 0
        return PosSale.objects.filter(status="settled").filter(
            Q(customer_id=obj.customer_id) | Q(online_order__customer_id=obj.customer_id)).count()
