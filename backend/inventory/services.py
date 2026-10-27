"""Everything that changes stock or money lives here, in one transaction each, so the ledger can't drift."""
from datetime import datetime, time
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers

from menu.pricing import money
from .models import (PurchaseInvoice, PurchaseInvoiceLine, PurchasePayment, RawMaterial, StockCount, StockCountLine,
                     StockMovement, default_warehouse)

THREE = Decimal("0.001")
FOUR = Decimal("0.0001")


def qty(value):
    return Decimal(value).quantize(THREE, rounding=ROUND_HALF_UP)


def stock_on_hand(material):
    return StockMovement.objects.filter(material=material).aggregate(t=Sum("quantity"))["t"] or Decimal("0")


def add_movement(material, quantity, movement_type, user, *, unit_cost=None, ref=None, note="", client_ref=None):
    return StockMovement.objects.create(
        warehouse=default_warehouse(), material=material, quantity=qty(quantity), movement_type=movement_type,
        unit_cost=unit_cost, reference_type=ref[0] if ref else "", reference_id=ref[1] if ref else None,
        note=note[:255], created_by=user, client_ref=client_ref)


def create_material_with_opening(serializer, user, opening_stock, opening_date=None):
    """opening_date: the day the stock was bought. The ledger row is dated then (not when it was typed in)."""
    with transaction.atomic():
        material = serializer.save()
        if opening_stock:
            mv = add_movement(material, opening_stock, "opening", user, note="Opening stock")
            if opening_date and opening_date < timezone.localdate():
                when = timezone.make_aware(datetime.combine(opening_date, time(12, 0)))
                StockMovement.objects.filter(pk=mv.pk).update(created_at=when)   # auto_now_add can't be set on create
    return material


@transaction.atomic
def post_purchase(user, d):
    """d: validated data of PurchaseCreateSerializer. Returns (invoice, created)."""
    ref = d.get("client_ref")
    if ref:
        existing = PurchaseInvoice.objects.filter(client_ref=ref).first()
        if existing:
            return existing, False

    lines, total = [], money(0)
    for raw in d["lines"]:
        m = raw["material"]
        line_total = money(raw["quantity"] * raw["unit_price"])
        lines.append((m, raw["quantity"], money(raw["unit_price"]), line_total, qty(raw["quantity"] * m.purchase_factor)))
        total += line_total

    paid_now = money(d.get("paid_now") or 0)
    if paid_now > total:
        raise serializers.ValidationError({"paid_now": "The amount paid can't be more than the invoice total."})

    invoice = PurchaseInvoice.objects.create(
        client_ref=ref, supplier=d["supplier"], invoice_number=d.get("invoice_number", "").strip(),
        invoice_date=d.get("invoice_date") or timezone.localdate(), notes=d.get("notes", "").strip(),
        total=total, amount_paid=paid_now, created_by=user)
    for m, q, price, line_total, stock_q in lines:
        PurchaseInvoiceLine.objects.create(
            invoice=invoice, material=m, quantity=q, unit_price=price, line_total=line_total,
            purchase_unit=m.purchase_unit, stock_quantity=stock_q)
        cost = (price / m.purchase_factor).quantize(FOUR, rounding=ROUND_HALF_UP)
        add_movement(m, stock_q, "purchase", user, unit_cost=cost, ref=("purchase_invoice", invoice.id),
                     note=f"{invoice.supplier.name} #{invoice.invoice_number}".strip(" #"))
    if paid_now > 0:
        PurchasePayment.objects.create(invoice=invoice, amount=paid_now, method=d.get("payment_method", "cash"), created_by=user)
    return invoice, True


class InventoryError(Exception):
    """A rule was broken; the message is meant for the manager."""


@transaction.atomic
def void_purchase(user, invoice_id, reason):
    """Reverse a posted bill: stock goes back out through new ledger rows (nothing is edited or deleted)."""
    invoice = PurchaseInvoice.objects.select_for_update().get(pk=invoice_id)
    if invoice.status != "posted":
        raise InventoryError("This invoice is already void.")
    for line in invoice.lines.select_related("material"):
        add_movement(line.material, -line.stock_quantity, "purchase_void", user, ref=("purchase_invoice", invoice.id),
                     note=f"Void: {reason}"[:255])
    invoice.status = "void"
    invoice.void_reason = reason[:255]
    invoice.voided_at = timezone.now()
    invoice.save(update_fields=["status", "void_reason", "voided_at"])
    return invoice


@transaction.atomic
def add_payment(user, invoice_id, amount, method):
    invoice = PurchaseInvoice.objects.select_for_update().get(pk=invoice_id)
    amount = money(amount)
    if invoice.status != "posted":
        raise InventoryError("A void invoice can't take payments.")
    if amount > invoice.balance_due:
        raise InventoryError(f"Only Rs. {invoice.balance_due} is still due on this invoice.")
    PurchasePayment.objects.create(invoice=invoice, amount=amount, method=method, created_by=user)
    invoice.amount_paid += amount
    invoice.save(update_fields=["amount_paid"])
    return invoice


def last_unit_cost(material):
    """Per stock unit, from the newest posted bill. None if it has never been bought."""
    return (StockMovement.objects.filter(
        material=material, movement_type="purchase", reference_type="purchase_invoice",
        reference_id__in=PurchaseInvoice.objects.filter(status="posted").values("id"))
        .order_by("-created_at", "-id").values_list("unit_cost", flat=True).first())


@transaction.atomic
def post_adjustment(user, d):
    """Waste, or a correction up or down. d: validated data of AdjustmentSerializer. Returns (movement, created)."""
    ref = d.get("client_ref")
    if ref:
        existing = StockMovement.objects.filter(client_ref=ref).first()
        if existing:
            return existing, False
    material = RawMaterial.objects.select_for_update().get(pk=d["material"].pk)
    amount = qty(d["quantity"])
    if d["direction"] == "out":
        have = stock_on_hand(material)
        if amount > have:
            raise serializers.ValidationError({"quantity": f"You only have {have.normalize():f} {material.stock_unit} of {material.name} in stock."})
        amount = -amount
    mv = add_movement(material, amount, d["kind"], user, unit_cost=last_unit_cost(material),
                      note=d["reason"].strip(), client_ref=ref)
    return mv, True


@transaction.atomic
def post_count(user, d):
    """Set stock to what was physically counted. Only the DIFFERENCE is written, as a new ledger row.
    d: validated data of CountCreateSerializer. Returns (count, created)."""
    ref = d.get("client_ref")
    if ref:
        existing = StockCount.objects.filter(client_ref=ref).first()
        if existing:
            return existing, False
    seen = set()
    for raw in d["lines"]:
        if raw["material"].pk in seen:
            raise serializers.ValidationError({"lines": f"{raw['material'].name} is in the count twice."})
        seen.add(raw["material"].pk)
    count = StockCount.objects.create(client_ref=ref, note=d.get("note", "").strip(), created_by=user)
    for raw in d["lines"]:
        material = RawMaterial.objects.select_for_update().get(pk=raw["material"].pk)
        expected = stock_on_hand(material)
        counted = qty(raw["counted"])
        diff = counted - expected
        cost = last_unit_cost(material)
        StockCountLine.objects.create(count=count, material=material, expected=expected, counted=counted, difference=diff, unit_cost=cost)
        if diff != 0:
            add_movement(material, diff, "count", user, unit_cost=cost, ref=("stock_count", count.id), note=count.note or "Stock count")
    return count, True
