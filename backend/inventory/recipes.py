"""Recipes (what a menu item size uses) and deal contents (which items a deal contains), with their cost."""
from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from menu.models import Deal, MenuItem, MenuItemPrice
from menu.pricing import money
from .consumption import latest_cost_map
from .models import DealComponent, RawMaterial, RecipeLine
from .reports import _m, _q

ZERO = Decimal("0")


class RecipeLineInput(serializers.Serializer):
    material = serializers.PrimaryKeyRelatedField(queryset=RawMaterial.objects.all())
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"), max_value=Decimal("999999"))


class RecipeInput(serializers.Serializer):
    lines = RecipeLineInput(many=True, max_length=60)

    def validate_lines(self, lines):
        ids = [l["material"].pk for l in lines]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Each raw material can appear only once. Add the amounts together.")
        for l in lines:
            if not l["material"].is_active:
                raise serializers.ValidationError(f"{l['material'].name} is retired. Un-retire it or remove it from the recipe.")
        return lines


class DealComponentInput(serializers.Serializer):
    price = serializers.PrimaryKeyRelatedField(queryset=MenuItemPrice.objects.select_related("menu_item"))
    quantity = serializers.IntegerField(min_value=1, max_value=99)


class DealContentsInput(serializers.Serializer):
    components = DealComponentInput(many=True, max_length=40)

    def validate_components(self, comps):
        ids = [c["price"].pk for c in comps]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Each menu item size can appear only once. Raise its quantity instead.")
        return comps


@transaction.atomic
def set_recipe(price, lines):
    RecipeLine.objects.filter(price=price).delete()
    RecipeLine.objects.bulk_create([RecipeLine(price=price, material=l["material"], quantity=l["quantity"]) for l in lines])


@transaction.atomic
def set_deal_contents(deal, comps):
    DealComponent.objects.filter(deal=deal).delete()
    DealComponent.objects.bulk_create([DealComponent(deal=deal, price=c["price"], quantity=c["quantity"]) for c in comps])


def _cost_block(sell_price, cost, complete):
    if cost is None:
        return {"cost": None, "margin": None, "margin_pct": None, "cost_complete": False}
    margin = Decimal(sell_price) - cost
    pct = (margin / Decimal(sell_price) * 100).quantize(Decimal("0.1")) if Decimal(sell_price) else None
    return {"cost": _m(cost), "margin": _m(margin), "margin_pct": None if pct is None else str(pct), "cost_complete": complete}


def overview():
    """Everything the Recipes screen needs in one call."""
    costs = latest_cost_map()
    lines_by_price = {}
    for r in RecipeLine.objects.select_related("material"):
        lines_by_price.setdefault(r.price_id, []).append(r)

    def price_cost(price_id):
        """(cost, complete) of one serving. cost is None when there is no recipe, or none of its ingredients has ever been bought."""
        rows = lines_by_price.get(price_id)
        if not rows:
            return None, False                          # no recipe at all
        total, complete, known = ZERO, True, False
        for r in rows:
            c = costs.get(r.material_id)
            if c is None:
                complete = False
            else:
                known = True
                total += r.quantity * c
        return (total if known else None), complete

    items = []
    for item in MenuItem.objects.select_related("category").prefetch_related("prices").order_by("category__order", "order", "name"):
        sizes = []
        for p in item.prices.all():
            rows = lines_by_price.get(p.pk, [])
            cost, complete = price_cost(p.pk)
            sizes.append({
                "price_id": p.pk, "label": p.label, "price": _m(p.price), "has_recipe": bool(rows),
                "lines": [{"material": r.material_id, "material_name": r.material.name, "stock_unit": r.material.stock_unit,
                           "quantity": _q(r.quantity)} for r in rows],
                **_cost_block(p.price, cost, complete),
            })
        items.append({"id": item.pk, "name": item.name, "category": item.category.name, "is_active": item.is_active, "sizes": sizes})

    deals = []
    for deal in Deal.objects.prefetch_related("components__price__menu_item").order_by("order", "id"):
        comps, total, complete, any_recipe = [], ZERO, True, False
        for c in deal.components.all():
            pc, pcomplete = price_cost(c.price_id)
            if pc is None:
                complete = False                       # no recipe, or nothing priced yet: the cost is understated
            else:
                any_recipe = True
                total += pc * c.quantity
                complete = complete and pcomplete
            comps.append({"price_id": c.price_id, "item_name": c.price.menu_item.name, "size_label": c.price.label,
                          "quantity": c.quantity, "has_recipe": c.price_id in lines_by_price})
        deals.append({"id": deal.pk, "name": deal.name, "price": _m(deal.price), "is_active": deal.is_active,
                      "components": comps, "has_items": bool(comps),
                      **_cost_block(deal.price, total if any_recipe else None, complete and bool(comps))})

    sizes_all = [s for i in items if i["is_active"] for s in i["sizes"]]
    return {
        "items": items, "deals": deals,
        "coverage": {"sizes": len(sizes_all), "with_recipe": sum(1 for s in sizes_all if s["has_recipe"])},
    }
