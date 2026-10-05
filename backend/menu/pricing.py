"""
Server-side pricing, shared by online orders and POS orders.

Clients only say WHAT they want (a price_id or a deal_id, and a quantity).
The server looks up the real price - a client can never choose its own price.
"""
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from rest_framework import serializers

from .models import Deal, MenuItemPrice

TWO_PLACES = Decimal("0.01")


def money(value):
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def calc_tax(taxable_amount):
    return money(Decimal(taxable_amount) * settings.TAX_RATE)


class OrderLineSerializer(serializers.Serializer):
    """
    Input:  price_id XOR deal_id, quantity.
    Output: the snapshot the customer was actually charged.
    """
    price_id = serializers.IntegerField(write_only=True, required=False, min_value=1)
    deal_id = serializers.IntegerField(write_only=True, required=False, min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=99)

    item_name = serializers.CharField(read_only=True)
    size_label = serializers.CharField(read_only=True)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    def validate(self, attrs):
        price_id = attrs.get("price_id")
        deal_id = attrs.get("deal_id")
        if bool(price_id) == bool(deal_id):
            raise serializers.ValidationError("Each line needs exactly one of price_id or deal_id.")

        if price_id:
            try:
                price = MenuItemPrice.objects.select_related("menu_item").get(
                    pk=price_id, menu_item__is_active=True
                )
            except MenuItemPrice.DoesNotExist:
                raise serializers.ValidationError({"price_id": "This item is not available."})
            attrs["_line"] = {
                "item_name": price.menu_item.name,
                "size_label": price.label,
                "unit_price": price.price,
                "menu_item": price.menu_item,
                "price": price,
                "deal": None,
            }
        else:
            try:
                deal = Deal.objects.get(pk=deal_id, is_active=True)
            except Deal.DoesNotExist:
                raise serializers.ValidationError({"deal_id": "This deal is not available."})
            attrs["_line"] = {
                "item_name": deal.name,
                "size_label": "Deal",
                "unit_price": deal.price,
                "menu_item": None,
                "price": None,
                "deal": deal,
            }
        return attrs


def build_lines(items_data):
    """Turn validated line input into model kwargs with server-set prices."""
    lines = []
    for item in items_data:
        line = dict(item["_line"])
        line["quantity"] = item["quantity"]
        line["unit_price"] = money(line["unit_price"])
        line["line_total"] = money(line["unit_price"] * item["quantity"])
        lines.append(line)
    return lines
