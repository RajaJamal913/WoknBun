"""
Stock used by sales. A sale line is turned into raw materials through recipes:

    menu item line  -> that size's recipe x quantity
    deal line       -> every component's recipe x component quantity x deal quantity

Items or deals with no recipe use nothing (they simply have no stock tracking yet).
Deduct and reverse are idempotent: they look at the ledger, so a retried request,
a double click or a re-delivered sync can never take stock out twice or put it back twice.
Inventory trouble must never lose a sale, so callers use `safely`.
"""
import logging
from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.db.models import OuterRef, Subquery

from .models import DealComponent, PurchaseInvoice, RawMaterial, RecipeLine, StockMovement
from .services import add_movement

log = logging.getLogger(__name__)
REF = "pos_order"


def latest_cost_map():
    """{material_id: latest purchase cost per stock unit}, ignoring voided invoices."""
    last = (StockMovement.objects.filter(
        material=OuterRef("pk"), movement_type="purchase", reference_type="purchase_invoice",
        reference_id__in=PurchaseInvoice.objects.filter(status="posted").values("id"))
        .order_by("-created_at", "-id").values("unit_cost")[:1])
    return {m.pk: m.c for m in RawMaterial.objects.annotate(c=Subquery(last)) if m.c is not None}


def recipes_for(price_ids):
    out = defaultdict(list)
    for r in RecipeLine.objects.filter(price_id__in=set(price_ids)):
        out[r.price_id].append((r.material_id, r.quantity))
    return out


def deal_recipe(deal_ids):
    """{deal_id: [(price_id, count)]}"""
    out = defaultdict(list)
    for c in DealComponent.objects.filter(deal_id__in=set(deal_ids)):
        out[c.deal_id].append((c.price_id, c.quantity))
    return out


def needs_for_items(items):
    """items: iterable of (price_id|None, deal_id|None, quantity). Returns {material_id: stock-unit quantity}."""
    items = list(items)
    comps = deal_recipe([d for _, d, _ in items if d])
    price_ids = [p for p, _, _ in items if p] + [p for lst in comps.values() for p, _ in lst]
    recipes = recipes_for(price_ids)
    need = defaultdict(Decimal)
    for price_id, deal_id, quantity in items:
        if price_id:
            for mid, q in recipes.get(price_id, []):
                need[mid] += q * quantity
        elif deal_id:
            for comp_price, count in comps.get(deal_id, []):
                for mid, q in recipes.get(comp_price, []):
                    need[mid] += q * count * quantity
    return need


def _order_needs(order):
    return needs_for_items((i.price_id, i.deal_id, i.quantity) for i in order.items.all())


def _rows(order, movement_type):
    return list(StockMovement.objects.filter(reference_type=REF, reference_id=order.pk, movement_type=movement_type))


def deduct_for_sale(order, user=None):
    """Take the order's ingredients out of stock, once. Returns True if it did."""
    if _rows(order, "sale"):
        return False
    need = _order_needs(order)
    if not need:
        return False
    costs = latest_cost_map()
    materials = RawMaterial.objects.in_bulk(list(need))
    for mid, q in need.items():
        add_movement(materials[mid], -q, "sale", user, unit_cost=costs.get(mid), ref=(REF, order.pk), note=f"Order #{order.pk}")
    return True


def reverse_for_sale(order, user=None):
    """Put back exactly what this order took, once. Returns True if it did."""
    sold = _rows(order, "sale")
    if not sold or _rows(order, "sale_reversal"):
        return False
    for row in sold:
        add_movement(row.material, -row.quantity, "sale_reversal", user, unit_cost=row.unit_cost,
                     ref=(REF, order.pk), note=f"Order #{order.pk} reversed")
    return True


def safely(fn, order, user=None):
    """Run fn in its own savepoint; a failure is logged and never stops the sale itself."""
    try:
        with transaction.atomic():
            return fn(order, user)
    except Exception:
        log.exception("Stock update failed for order %s", getattr(order, "pk", None))
        return False
