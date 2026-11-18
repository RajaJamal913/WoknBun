"""
The cash count for a shift, split by restaurant.

Wok & Bun keeps its sales in pos.Order; Cor and Shangyaki each keep theirs in their own app. Every
one of them has the same Order / Settlement / Refund shape, so the shift can add them all up and
still show which restaurant each rupee came from.

  cash / card sales  = orders sold on THIS shift (settled or refunded), by how they were paid
  cash refunds       = refunds this cashier paid out while the shift was open, on cash-paid orders
  expected in drawer = opening cash + cash sales - cash refunds   (card money never touches the drawer)
"""
from decimal import Decimal

from django.apps import apps
from django.db.models import Count, Sum
from django.utils import timezone

ZERO = Decimal("0.00")

# (slug, name shown on screen, app label that owns the Order / Settlement / Refund models)
RESTAURANTS = [
    ("woknbun", "Wok & Bun", "pos"),
    ("cor", "Cor", "cor"),
    ("shangyaki", "Shangyaki", "shangyaki"),
]


def _money(value):
    return str((value or ZERO).quantize(ZERO))


def _models(label):
    try:
        return (apps.get_model(label, "Order"), apps.get_model(label, "Settlement"), apps.get_model(label, "Refund"))
    except LookupError:  # that restaurant's app isn't installed on this server
        return None


def restaurant_summary(shift, slug, name, label):
    found = _models(label)
    if found is None:
        return None
    Order, Settlement, Refund = found

    on_shift = Order.objects.filter(shift_id=shift.id)
    sold = on_shift.filter(status__in=["settled", "refunded"])

    def paid_by(method):
        agg = Settlement.objects.filter(order__in=sold, payment_method=method).aggregate(n=Count("id"), t=Sum("order__grand_total"))
        return agg["n"] or 0, agg["t"] or ZERO

    cash_n, cash_sales = paid_by("cash")
    card_n, card_sales = paid_by("card")

    until = shift.closed_at or timezone.now()
    refunds = Refund.objects.filter(cashier_id=shift.cashier_id, refunded_at__gte=shift.opened_at, refunded_at__lte=until)
    cash_refunds = refunds.filter(order__settlement__payment_method="cash").aggregate(t=Sum("amount"))["t"] or ZERO
    card_refunds = refunds.filter(order__settlement__payment_method="card").aggregate(t=Sum("amount"))["t"] or ZERO

    return {
        "slug": slug, "name": name,
        "orders": sold.count(),
        "cash_orders": cash_n, "cash_sales": _money(cash_sales), "cash_refunds": _money(cash_refunds),
        "card_orders": card_n, "card_sales": _money(card_sales), "card_refunds": _money(card_refunds),
        "net_cash": _money(cash_sales - cash_refunds),
        "net_sales": _money(cash_sales + card_sales - cash_refunds - card_refunds),
        "open_orders": on_shift.filter(status="open").count(),
        "cancelled_orders": on_shift.filter(status="cancelled").count(),
    }


def shift_summary(shift):
    rows = [r for r in (restaurant_summary(shift, *spec) for spec in RESTAURANTS) if r is not None]
    cash_in = sum((Decimal(r["cash_sales"]) for r in rows), ZERO)
    cash_out = sum((Decimal(r["cash_refunds"]) for r in rows), ZERO)
    return {
        "shift": shift.id,
        "opening_cash": _money(shift.opening_cash),
        "restaurants": rows,
        "cash_sales": _money(cash_in),
        "cash_refunds": _money(cash_out),
        "expected_cash": _money(shift.opening_cash + cash_in - cash_out),
    }


def open_orders_by_restaurant(shift):
    """[(name, how many unpaid orders)] for every restaurant that still has unpaid orders on this shift."""
    out = []
    for slug, name, label in RESTAURANTS:
        found = _models(label)
        if found is None:
            continue
        n = found[0].objects.filter(shift_id=shift.id, status="open").count()
        if n:
            out.append((name, n))
    return out
