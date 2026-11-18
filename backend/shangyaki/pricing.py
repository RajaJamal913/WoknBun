"""Server-side pricing. Clients say WHAT they want (price_id / deal_id + quantity); the server sets the price."""
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from rest_framework import serializers

from .models import Deal, MenuItemPrice

TWO_PLACES = Decimal("0.01")


def money(value):
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def calc_tax(amount):
    return money(Decimal(amount) * settings.TAX_RATE)


class OrderLineSerializer(serializers.Serializer):
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

        # The website sells only what is on the menu now. The POS passes allow_inactive_menu: the
        # cashier already served the customer from their screen, so a sale must not be lost because
        # an item was hidden in the meantime.
        only_active = not self.context.get("allow_inactive_menu", False)

        if price_id:
            lookup = {"pk": price_id}
            if only_active:
                lookup["menu_item__is_active"] = True
            try:
                price = MenuItemPrice.objects.select_related("menu_item").get(**lookup)
            except MenuItemPrice.DoesNotExist:
                raise serializers.ValidationError({"price_id": "This item is not available."})
            attrs["_line"] = {
                "item_name": price.menu_item.name, "size_label": price.label,
                "unit_price": price.price, "menu_item": price.menu_item, "price": price, "deal": None,
            }
        else:
            lookup = {"pk": deal_id}
            if only_active:
                lookup["is_active"] = True
            try:
                deal = Deal.objects.get(**lookup)
            except Deal.DoesNotExist:
                raise serializers.ValidationError({"deal_id": "This deal is not available."})
            attrs["_line"] = {
                "item_name": deal.name, "size_label": "Deal",
                "unit_price": deal.price, "menu_item": None, "price": None, "deal": deal,
            }
        return attrs


def build_lines(items_data):
    lines = []
    for item in items_data:
        line = dict(item["_line"])
        line["quantity"] = item["quantity"]
        line["unit_price"] = money(line["unit_price"])
        line["line_total"] = money(line["unit_price"] * item["quantity"])
        lines.append(line)
    return lines
