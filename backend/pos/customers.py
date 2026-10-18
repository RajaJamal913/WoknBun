"""
Customer queries for the POS: search, profile, stats, history.

"Spent" and "orders" count SETTLED sales only (so refunded and cancelled orders
never inflate a customer's numbers) - the same net basis the reports use.
"""
from decimal import Decimal

from django.db.models import Count, F, Max, Min, Q, Sum

from accounts.models import Customer
from accounts.phone import search_digits
from orders.models import Order as WebOrder
from .models import Order as Sale, OrderItem

ZERO = Decimal("0.00")
LIST_LIMIT = 30
HISTORY_LIMIT = 50


def _money(v):
    return str(Decimal(v or 0).quantize(ZERO))


def with_stats(qs):
    settled = Q(pos_orders__status="settled")
    return qs.annotate(
        orders_count=Count("pos_orders", filter=settled),
        total_spent=Sum("pos_orders__grand_total", filter=settled, default=ZERO),
        last_order_at=Max("pos_orders__created_at", filter=settled),
    )


def search(query):
    qs = with_stats(Customer.objects.all())
    query = (query or "").strip()
    if query:
        cond = Q(full_name__icontains=query) | Q(email__icontains=query)
        digits = search_digits(query)
        if len(digits) >= 3:
            cond |= Q(phone__contains=digits) | Q(alt_phone__contains=digits)
        return qs.filter(cond).order_by("full_name")[:LIST_LIMIT]
    return qs.order_by(F("last_order_at").desc(nulls_last=True), "-created_at")[:LIST_LIMIT]


def summary(c):
    """One row of a list. `c` must come from with_stats()."""
    return {
        "id": c.id, "full_name": c.full_name, "phone": c.phone or "", "email": c.email,
        "has_account": c.has_account,
        "orders_count": c.orders_count, "total_spent": _money(c.total_spent),
        "last_order_at": c.last_order_at.isoformat() if c.last_order_at else None,
    }


def _items_text(items):
    def one(i):
        size = f" ({i.size_label})" if i.size_label and i.size_label != "Regular" else ""
        return f"{i.quantity}x {i.item_name}{size}"
    return ", ".join(one(i) for i in items)


def detail(customer_id):
    c = with_stats(Customer.objects.filter(pk=customer_id)).first()
    if c is None:
        return None
    # A sale belongs to this customer if it is linked to them directly (counter orders) OR through the website
    # order it came from. Using both means an older sale that was never linked directly still shows up.
    mine = Q(customer=c) | Q(online_order__customer=c)
    sold = Sale.objects.filter(mine, status="settled").aggregate(
        n=Count("id"), total=Sum("grand_total"), first=Min("created_at"), last=Max("created_at"))
    orders_count, total_spent = sold["n"], sold["total"] or ZERO
    avg = (Decimal(total_spent) / orders_count) if orders_count else ZERO

    favourites = [
        {"item_name": r["item_name"], "size_label": r["size_label"], "quantity": r["q"]}
        for r in OrderItem.objects.filter(Q(order__customer=c) | Q(order__online_order__customer=c), order__status="settled")
        .values("item_name", "size_label").annotate(q=Sum("quantity")).order_by("-q", "item_name")[:3]
    ]
    addresses = [
        {"address_line": r["address_line"], "last_used": r["last"].isoformat(), "orders": r["n"]}
        for r in WebOrder.objects.filter(customer=c).values("address_line")
        .annotate(last=Max("created_at"), n=Count("id")).order_by("-last")[:5]
    ]

    rows = []
    for s in Sale.objects.filter(mine).select_related("online_order").prefetch_related("items").order_by("-created_at")[:HISTORY_LIMIT]:
        rows.append({"kind": "sale", "id": s.id, "when": s.created_at, "type": s.order_type, "status": s.status,
                     "total": _money(s.grand_total), "items": _items_text(s.items.all()),
                     "address": s.online_order.address_line if s.online_order else ""})
    # website orders that never became a sale (still waiting, or turned down)
    for w in WebOrder.objects.filter(customer=c, pos_order__isnull=True).prefetch_related("items").order_by("-created_at")[:HISTORY_LIMIT]:
        rows.append({"kind": "website", "id": w.id, "when": w.created_at, "type": "online", "status": w.status,
                     "total": _money(w.grand_total), "items": _items_text(w.items.all()), "address": w.address_line})
    rows.sort(key=lambda r: r["when"], reverse=True)
    for r in rows:
        r["when"] = r["when"].isoformat()

    return {
        "id": c.id, "full_name": c.full_name, "phone": c.phone or "", "alt_phone": c.alt_phone, "email": c.email,
        "notes": c.notes, "created_at": c.created_at.isoformat(),
        "has_account": c.has_account, "account_created_at": c.account_created_at.isoformat() if c.account_created_at else None,
        "last_login_at": c.last_login_at.isoformat() if c.last_login_at else None,
        "stats": {
            "orders_count": orders_count, "total_spent": _money(total_spent), "avg_order": _money(avg),
            "first_order_at": sold["first"].isoformat() if sold["first"] else None,
            "last_order_at": sold["last"].isoformat() if sold["last"] else None,
        },
        "favourites": favourites, "addresses": addresses, "orders": rows[:HISTORY_LIMIT],
    }