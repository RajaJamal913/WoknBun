"""
Inventory reports. Stock on hand is always the sum of the ledger, so every report agrees with the others.
Days are local business days (settings.TIME_ZONE), like the sales reports.
"""
from decimal import Decimal

from django.utils import timezone

from django.db.models import Count, DecimalField, ExpressionWrapper, F, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce

from pos.reports import day_range
from .models import PurchaseInvoice, PurchaseInvoiceLine, RawMaterial, StockMovement

ZERO = Decimal("0")
MONEY0 = Decimal("0.00")


def _m(v):
    return str((v or MONEY0).quantize(Decimal("0.01")))


def _q(v):
    """Quantities show without trailing zeros: 2.500 -> 2.5, 1000.000 -> 1000."""
    s = format(Decimal(v or 0).quantize(Decimal("0.001")), "f")
    return s.rstrip("0").rstrip(".") if "." in s else s


def stock_summary():
    last_cost = (StockMovement.objects.filter(
        material=OuterRef("pk"), movement_type="purchase", reference_type="purchase_invoice",
        reference_id__in=PurchaseInvoice.objects.filter(status="posted").values("id"))
        .order_by("-created_at", "-id").values("unit_cost")[:1])
    # The day it was last bought: the date on the newest posted bill that includes it, or the day its opening stock was bought.
    last_bill = (PurchaseInvoiceLine.objects.filter(material=OuterRef("pk"), invoice__status="posted")
                 .order_by("-invoice__invoice_date", "-invoice_id").values("invoice__invoice_date")[:1])
    last_opening = (StockMovement.objects.filter(material=OuterRef("pk"), movement_type="opening")
                    .order_by("-created_at", "-id").values("created_at")[:1])
    rows = RawMaterial.objects.annotate(
        on_hand=Coalesce(Sum("movements__quantity"), ZERO, output_field=DecimalField()),
        last_cost=Subquery(last_cost), last_bill_date=Subquery(last_bill), last_opening_at=Subquery(last_opening)).order_by("name")

    out, total_value, low = [], ZERO, 0
    for r in rows:
        if not r.is_active and r.on_hand == 0:
            continue                                   # retired and empty: nothing to show
        value = (r.on_hand * r.last_cost) if (r.last_cost is not None and r.on_hand > 0) else ZERO
        is_low = r.reorder_level > 0 and r.on_hand <= r.reorder_level
        total_value += value
        low += 1 if is_low else 0
        days = [d for d in (r.last_bill_date, timezone.localtime(r.last_opening_at).date() if r.last_opening_at else None) if d]
        out.append({
            "id": r.id, "name": r.name, "is_active": r.is_active,
            "stock_unit": r.stock_unit, "on_hand": _q(r.on_hand),
            "purchase_unit": r.purchase_unit,
            "purchase_factor": _q(r.purchase_factor),
            "on_hand_purchase": _q(r.on_hand / r.purchase_factor) if r.purchase_factor else _q(r.on_hand),
            "reorder_level": _q(r.reorder_level), "low": is_low, "negative": r.on_hand < 0,
            "last_cost": None if r.last_cost is None else str(Decimal(r.last_cost).quantize(Decimal("0.0001"))),
            "value": _m(value),
            "last_bought": max(days).isoformat() if days else None,
        })
    return {"materials": out, "total_value": _m(total_value), "low_count": low,
            "value_note": "Value uses each material's most recent purchase cost."}


LABELS = dict(StockMovement.TYPE_CHOICES)


def stock_ledger(material, date_from, date_to):
    start, end = day_range(date_from, date_to)
    before = StockMovement.objects.filter(material=material, created_at__lt=start).aggregate(t=Sum("quantity"))["t"] or ZERO
    moves = (StockMovement.objects.filter(material=material, created_at__gte=start, created_at__lt=end)
             .select_related("created_by").order_by("created_at", "id"))
    balance, rows, total_in, total_out = before, [], ZERO, ZERO
    for mv in moves:
        balance += mv.quantity
        total_in += mv.quantity if mv.quantity > 0 else ZERO
        total_out += -mv.quantity if mv.quantity < 0 else ZERO
        rows.append({
            "time": mv.created_at.isoformat(), "type": mv.movement_type, "label": LABELS.get(mv.movement_type, mv.movement_type),
            "reference": f"{mv.reference_type.replace('_', ' ')} #{mv.reference_id}" if mv.reference_id else "",
            "note": mv.note, "qty_in": _q(mv.quantity) if mv.quantity > 0 else "", "qty_out": _q(-mv.quantity) if mv.quantity < 0 else "",
            "balance": _q(balance),
            "by": (mv.created_by.get_full_name() or mv.created_by.get_username()) if mv.created_by else "",
        })
    return {
        "material": {"id": material.id, "name": material.name, "stock_unit": material.stock_unit},
        "from": date_from.isoformat(), "to": date_to.isoformat(),
        "opening": _q(before), "total_in": _q(total_in), "total_out": _q(total_out), "closing": _q(balance),
        "rows": rows,
    }


def purchase_report(date_from, date_to, supplier_id=None):
    invoices = (PurchaseInvoice.objects.filter(invoice_date__gte=date_from, invoice_date__lte=date_to)
                .select_related("supplier").order_by("invoice_date", "id"))
    if supplier_id:
        invoices = invoices.filter(supplier_id=supplier_id)
    posted = invoices.filter(status="posted")
    agg = posted.aggregate(n=Count("id"), total=Sum("total"), paid=Sum("amount_paid"))
    total, paid = agg["total"] or MONEY0, agg["paid"] or MONEY0
    by_supplier = [
        {"supplier": r["supplier__name"], "invoices": r["n"], "total": _m(r["t"]), "paid": _m(r["p"]), "due": _m(r["t"] - r["p"])}
        for r in posted.values("supplier__name").annotate(n=Count("id"), t=Sum("total"), p=Sum("amount_paid")).order_by("-t")
    ]
    return {
        "from": date_from.isoformat(), "to": date_to.isoformat(),
        "invoices": [{
            "id": i.id, "date": i.invoice_date.isoformat(), "supplier": i.supplier.name, "invoice_number": i.invoice_number,
            "status": i.status, "total": _m(i.total), "paid": _m(i.amount_paid),
            "due": _m(i.balance_due) if i.status == "posted" else "0.00"} for i in invoices],
        "count": agg["n"] or 0, "total": _m(total), "paid": _m(paid), "due": _m(total - paid),
        "voided_count": invoices.filter(status="void").count(),
        "by_supplier": by_supplier,
        "note": "Totals count posted invoices only; voided ones are listed but not added up.",
    }
