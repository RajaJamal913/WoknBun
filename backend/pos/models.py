import uuid
from django.conf import settings
from django.db import models


class StaffProfile(models.Model):
    """Extends Django's built-in User with the role POS permissions need."""
    ROLE_CHOICES = [
        ("cashier", "Cashier"),
        ("kitchen", "Kitchen"),
        ("manager", "Manager"),
        ("admin", "Admin"),
    ]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="staff_profile")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="cashier")

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.role})"


class Shift(models.Model):
    STATUS_CHOICES = [("open", "Open"), ("closed", "Closed")]

    cashier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="shifts")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="open")
    opening_cash = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    closing_cash = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-opened_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["cashier"], condition=models.Q(status="open"),
                name="one_open_shift_per_cashier",
            ),
        ]

    def __str__(self):
        return f"Shift #{self.id} - {self.cashier} ({self.status})"


class Order(models.Model):
    """
    A counter/dine-in order punched at the POS terminal. Deliberately
    separate from orders.Order (the online-delivery model) - different
    lifecycle, different fields (shift, table, settlement, refund).
    """
    ORDER_TYPE_CHOICES = [("dine_in", "Dine In"), ("takeaway", "Takeaway"), ("counter", "Counter")]
    STATUS_CHOICES = [
        ("open", "Open"),
        ("settled", "Settled"),
        ("refunded", "Refunded"),
        ("cancelled", "Cancelled"),
    ]

    # Generated client-side (on the Electron terminal) so the same order
    # can be safely retried/re-synced without ever creating a duplicate -
    # essential once the terminal is queuing orders made while offline.
    client_order_id = models.UUIDField(unique=True, default=uuid.uuid4)

    shift = models.ForeignKey(Shift, on_delete=models.PROTECT, related_name="orders")
    order_type = models.CharField(max_length=10, choices=ORDER_TYPE_CHOICES, default="counter")
    table_label = models.CharField(max_length=40, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="open")

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    settled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.id} ({self.status})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    item_name = models.CharField(max_length=150)
    size_label = models.CharField(max_length=40, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)
    # Snapshot fields above (name/size/price) are what the customer was
    # charged and never change. These links tie the line back to the live
    # menu so reports and stock can group by real items.
    menu_item = models.ForeignKey("menu.MenuItem", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    price = models.ForeignKey("menu.MenuItemPrice", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    deal = models.ForeignKey("menu.Deal", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    def __str__(self):
        return f"{self.quantity} x {self.item_name}"


class Settlement(models.Model):
    PAYMENT_CHOICES = [("cash", "Cash"), ("card", "Card")]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="settlement")
    cashier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="settlements")
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES)
    amount_tendered = models.DecimalField(max_digits=10, decimal_places=2)
    change_due = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    settled_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Settlement for Order #{self.order_id}"


class Refund(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="refund")
    cashier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="refunds")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255, blank=True)
    refunded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Refund for Order #{self.order_id}"