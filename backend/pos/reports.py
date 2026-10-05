"""
Sales reporting. Every figure is on the same basis so reports always agree:

  * "sold" orders  = settled or refunded, grouped by the day they were SETTLED
  * refunds        = grouped by the day the REFUND happened
  * net sales      = sold total - refunds  (== grand_total of orders still 'settled')
  * item / hourly reports use orders still 'settled' (i.e. already net of refunds)

Days are local business days (settings.TIME_ZONE), not UTC days.
"""
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import ExtractHour
from django.utils import timezone

from .models import Order, OrderItem, Refund, Settlement, Shift

ZERO = Decimal("0.00")


def day_range(date_from, date_to):
    """Local [start, end) datetimes covering date_from..date_to inclusive."""
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(date_from, time.min), tz)
    end = timezone.make_aware(datetime.combine(date_to + timedelta(days=1), time.min), tz)
    return start, end


def _money(value):
    return str((value or ZERO).quantize(ZERO))


def _sold(start, end):
    return Order.objects.filter(status__in=["settled", "refunded"], settled_at__gte=start, settled_at__lt=end)


def _net(start, end):
    return Order.objects.filter(status="settled", settled_at__gte=start, settled_at__lt=end)


def sales_summary(date_from, date_to):
    start, end = day_range(date_from, date_to)
    sold = _sold(start, end)
    agg = sold.aggregate(
        orders=Count("id"),
        items_total=Sum("subtotal"),
        discounts=Sum("discount_amount"),
        tax=Sum("tax_amount"),
        total_sales=Sum("grand_total"),
    )
    refunds = Refund.objects.filter(refunded_at__gte=start, refunded_at__lt=end).aggregate(
        count=Count("id"), total=Sum("amount"))
    total_sales = agg["total_sales"] or ZERO
    refunds_total = refunds["total"] or ZERO
    net_sales = total_sales - refunds_total
    refunded_orders = sold.filter(status="refunded").count()
    kept_orders = (agg["orders"] or 0) - refunded_orders

    by_type = [
        {"order_type": r["order_type"], "orders": r["n"], "total": _money(r["t"])}
        for r in sold.values("order_type").annotate(n=Count("id"), t=Sum("grand_total")).order_by("-t")
    ]
    by_payment = [
        {"payment_method": r["payment_method"], "orders": r["n"], "total": _money(r["t"])}
        for r in Settlement.objects.filter(order__in=sold)
        .values("payment_method").annotate(n=Count("id"), t=Sum("order__grand_total")).order_by("-t")
    ]
    cancelled = Order.objects.filter(status="cancelled", created_at__gte=start, created_at__lt=end).count()

    return {
        "from": date_from.isoformat(), "to": date_to.isoformat(),
        "orders": agg["orders"] or 0,
        "items_total": _money(agg["items_total"]),
        "discounts": _money(agg["discounts"]),
        "tax": _money(agg["tax"]),
        "total_sales": _money(total_sales),
        "refunds_count": refunds["count"] or 0,
        "refunds_total": _money(refunds_total),
        "net_sales": _money(net_sales),
        "avg_order_value": _money(net_sales / kept_orders) if kept_orders > 0 else _money(ZERO),
        "cancelled_orders": cancelled,
        "by_order_type": by_type,
        "by_payment": by_payment,
    }


def item_sales(date_from, date_to):
    """Item-wise sales (net of refunds), best sellers first."""
    start, end = day_range(date_from, date_to)
    rows = (
        OrderItem.objects.filter(order__in=_net(start, end))
        .values("menu_item__category__name", "item_name", "size_label")
        .annotate(quantity=Sum("quantity"), amount=Sum("line_total"))
        .order_by("-amount", "item_name")
    )
    items = [
        {
            "category": r["menu_item__category__name"] or ("Deals" if r["size_label"] == "Deal" else "Other"),
            "item_name": r["item_name"], "size_label": r["size_label"],
            "quantity": r["quantity"], "amount": _money(r["amount"]),
        }
        for r in rows
    ]
    return {
        "from": date_from.isoformat(), "to": date_to.isoformat(),
        "items": items,
        "total_quantity": sum(i["quantity"] for i in items),
        "total_amount": _money(sum((Decimal(i["amount"]) for i in items), ZERO)),
    }


def hourly_sales(day):
    start, end = day_range(day, day)
    rows = (
        _net(start, end).annotate(hour=ExtractHour("settled_at"))
        .values("hour").annotate(n=Count("id"), t=Sum("grand_total"))
    )
    by_hour = {r["hour"]: r for r in rows}
    hours = [
        {"hour": h, "label": f"{h:02d}:00", "orders": by_hour.get(h, {}).get("n", 0),
         "total": _money(by_hour.get(h, {}).get("t"))}
        for h in range(24)
    ]
    return {
        "date": day.isoformat(), "hours": hours,
        "total_orders": sum(h["orders"] for h in hours),
        "total_sales": _money(sum((Decimal(h["total"]) for h in hours), ZERO)),
    }


def cancellations(date_from, date_to):
    """
    Cancelled = voided BEFORE payment ("unmade": nothing was collected).
    Refunded  = reversed AFTER payment ("made": food was punched and paid for).
    (The terminal has no kitchen status yet, so this is the closest honest split.)
    """
    start, end = day_range(date_from, date_to)
    cancelled = (
        Order.objects.filter(status="cancelled", created_at__gte=start, created_at__lt=end)
        .select_related("shift__cashier").prefetch_related("items").order_by("-created_at")
    )
    refunds = (
        Refund.objects.filter(refunded_at__gte=start, refunded_at__lt=end)
        .select_related("order", "cashier").order_by("-refunded_at")
    )
    cancelled_rows = [
        {
            "order_id": o.id, "time": o.created_at.isoformat(), "order_type": o.order_type,
            "cashier": o.shift.cashier.get_full_name() or o.shift.cashier.get_username(),
            "items": ", ".join(f"{i.quantity}x {i.item_name}" for i in o.items.all()),
            "total": _money(o.grand_total),
        }
        for o in cancelled
    ]
    refund_rows = [
        {
            "order_id": r.order_id, "time": r.refunded_at.isoformat(),
            "refunded_by": r.cashier.get_full_name() or r.cashier.get_username(),
            "reason": r.reason, "total": _money(r.amount),
        }
        for r in refunds
    ]
    return {
        "from": date_from.isoformat(), "to": date_to.isoformat(),
        "cancelled": cancelled_rows,
        "cancelled_total": _money(sum((Decimal(r["total"]) for r in cancelled_rows), ZERO)),
        "refunds": refund_rows,
        "refunds_total": _money(sum((Decimal(r["total"]) for r in refund_rows), ZERO)),
    }


def dashboard(day):
    summary = sales_summary(day, day)
    previous = sales_summary(day - timedelta(days=1), day - timedelta(days=1))
    top = item_sales(day, day)["items"]
    top = sorted(top, key=lambda i: -i["quantity"])[:5]

    start, end = day_range(day, day)
    shifts = []
    for s in Shift.objects.filter(status="open").select_related("cashier"):
        net = s.orders.filter(status="settled").aggregate(t=Sum("grand_total"), n=Count("id"))
        shifts.append({
            "shift_id": s.id,
            "cashier": s.cashier.get_full_name() or s.cashier.get_username(),
            "opened_at": s.opened_at.isoformat(), "opening_cash": _money(s.opening_cash),
            "orders": net["n"] or 0, "sales": _money(net["t"]),
        })

    return {
        "date": day.isoformat(),
        "summary": summary,
        "previous_day_net_sales": previous["net_sales"],
        "open_orders": Order.objects.filter(status="open").count(),
        "hourly": hourly_sales(day)["hours"],
        "top_items": top,
        "open_shifts": shifts,
    }