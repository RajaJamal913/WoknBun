"""Everything that changes stock or money lives here, in one transaction each, so the ledger can't drift."""
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers

from menu.pricing import money
from .models import (PurchaseInvoice, PurchaseInvoiceLine, PurchasePayment, StockMovement, default_warehouse)

THREE = Decimal("0.001")
FOUR = Decimal("0.0001")


def qty(value):
    return Decimal(value).quantize(THREE, rounding=ROUND_HALF_UP)


def stock_on_hand(material):
    return StockMovement.objects.filter(material=material).aggregate(t=Sum("quantity"))["t"] or Decimal("0")


def add_movement(material, quantity, movement_type, user, *, unit_cost=None, ref=None, note=""):
    return StockMovement.objects.create(
        warehouse=default_warehouse(), material=material, quantity=qty(quantity), movement_type=movement_type,
        unit_cost=unit_cost, reference_type=ref[0] if ref else "", reference_id=ref[1] if ref else None,
        note=note[:255], created_by=user)


def create_material_with_opening(serializer, user, opening_stock):
    with transaction.atomic():
        material = serializer.save()
        if opening_stock:
            add_movement(material, opening_stock, "opening", user, note="Opening stock")
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
