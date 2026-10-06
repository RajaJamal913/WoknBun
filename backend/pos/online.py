"""
Working website (online) orders from the POS.

Lifecycle   pending -> confirmed -> preparing -> out_for_delivery -> delivered
                 \\______________ cancelled (with a reason) ______________/

  accept   creates the sale: a POS order linked to the website order, placed on
           the accepting cashier's open shift. From here it behaves like any POS
           sale (history, receipts, reports, refunds).
  deliver  the customer pays cash on delivery: the sale is settled for the exact
           total, on the shift of whoever records the delivery (they hold the cash).
  cancel   needs a reason; also cancels the sale if one exists.

Every change runs in a transaction on a row-locked order, so a double-click or a
second terminal can never apply the same step twice.
"""
import uuid

from django.db import transaction
from django.http import Http404
from django.utils import timezone

from orders.models import Order as OnlineOrder
from .models import Order as PosOrder, OrderItem as PosOrderItem, Settlement, Shift


class OnlineOrderError(Exception):
    """A rule was broken (wrong status, no open shift, ...). The message is meant for staff."""


LABELS = dict(OnlineOrder.STATUS_CHOICES)

TRANSITIONS = {
    #  action     allowed from                                         to                  as a phrase
    "accept":   ({"pending"},                                          "confirmed",        "accepted"),
    "prepare":  ({"confirmed"},                                        "preparing",        "moved to preparing"),
    "dispatch": ({"confirmed", "preparing"},                           "out_for_delivery", "sent out for delivery"),
    "deliver":  ({"confirmed", "preparing", "out_for_delivery"},       "delivered",        "marked delivered"),
    "cancel":   ({"pending", "confirmed", "preparing", "out_for_delivery"}, "cancelled",   "cancelled"),
}


def _open_shift(user, message):
    shift = Shift.objects.filter(cashier=user, status="open").first()
    if shift is None:
        raise OnlineOrderError(message)
    return shift


def _create_sale(order, shift):
    """Mirror the website order as a POS sale. Totals are copied, never recomputed:
    the customer saw and agreed to exactly these numbers."""
    sale = PosOrder.objects.create(
        client_order_id=uuid.uuid4(), shift=shift, order_type="online", online_order=order,
        subtotal=order.subtotal, discount_amount=0, tax_amount=order.tax_amount,
        delivery_charges=order.delivery_charges, grand_total=order.grand_total,
    )
    PosOrderItem.objects.bulk_create([
        PosOrderItem(order=sale, item_name=i.item_name, size_label=i.size_label, unit_price=i.unit_price,
                     quantity=i.quantity, line_total=i.line_total, menu_item=i.menu_item, price=i.price, deal=i.deal)
        for i in order.items.all()
    ])
    return sale


def apply_action(order_id, action, user, reason=""):
    """Apply one step. Returns (website_order, pos_sale_or_None)."""
    if action not in TRANSITIONS:
        raise OnlineOrderError("Unknown action.")
    allowed_from, new_status, phrase = TRANSITIONS[action]
    reason = (reason or "").strip()

    with transaction.atomic():
        try:
            order = OnlineOrder.objects.select_for_update().get(pk=order_id)
        except OnlineOrder.DoesNotExist:
            raise Http404("Order not found.")
        if order.status not in allowed_from:
            raise OnlineOrderError(f"Order #{order.id} is {LABELS[order.status]}, so it can't be {phrase} now.")

        sale = PosOrder.objects.select_for_update().filter(online_order=order).first()

        if action == "accept":
            shift = _open_shift(user, "Open a shift before accepting online orders - the sale is counted in your shift.")
            sale = _create_sale(order, shift)
            order.accepted_by = user

        elif action == "deliver":
            shift = _open_shift(user, "Open a shift before recording a delivery - the cash you collect is counted in your shift.")
            if sale is None or sale.status != "open":
                raise OnlineOrderError("This order has no open sale to settle. Ask a manager.")
            sale.shift = shift  # the cash is now in this cashier's drawer
            sale.status = "settled"
            sale.settled_at = timezone.now()
            sale.save(update_fields=["shift", "status", "settled_at"])
            Settlement.objects.create(order=sale, cashier=user, payment_method="cash",
                                      amount_tendered=sale.grand_total, change_due=0)

        elif action == "cancel":
            if not reason:
                raise OnlineOrderError("Enter a reason for cancelling this order.")
            order.cancel_reason = reason[:255]
            if sale is not None and sale.status == "open":
                sale.status = "cancelled"
                sale.cancel_reason = order.cancel_reason
                sale.cancelled_at = timezone.now()
                sale.save(update_fields=["status", "cancel_reason", "cancelled_at"])

        order.status = new_status
        order.status_changed_at = timezone.now()
        order.save()
    return order, sale