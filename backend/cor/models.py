"""Cor - its own menu and its own orders, separate from every other restaurant."""
from django.conf import settings
from django.db import models
from django.utils.text import slugify


# ---------------------------------------------------------------- menu

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    BADGE_CHOICES = [
        ("", "None"),
        ("best_seller", "Best Seller"),
        ("new", "New"),
    ]

    category = models.ForeignKey(Category, related_name="items", on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    description = models.CharField(max_length=255, blank=True)
    note = models.CharField(max_length=255, blank=True, help_text="Small print shown under the item")
    image_url = models.URLField(blank=True)
    badge = models.CharField(max_length=20, choices=BADGE_CHOICES, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name} ({self.category.name})"


class MenuItemPrice(models.Model):
    """One price (blank label) or several size/variant prices (Single/Double, Small..XL)."""
    menu_item = models.ForeignKey(MenuItem, related_name="prices", on_delete=models.CASCADE)
    label = models.CharField(max_length=40, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.menu_item.name} - {self.label or 'Price'}: Rs. {self.price}"


class Deal(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(help_text="One line per item, e.g. '2 Chicken Burgers'")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    badge = models.CharField(max_length=100, blank=True, help_text="e.g. '2 Mint Margarita Complimentary'")
    image_url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------- orders

class Order(models.Model):
    PAYMENT_CHOICES = [("cod", "Cash On Delivery")]
    # Website orders move pending -> ... -> delivered. A sale rung up at the POS is
    # open (not paid yet) -> settled (paid) -> refunded, or cancelled before payment.
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("preparing", "Preparing"),
        ("out_for_delivery", "Out For Delivery"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
        ("open", "Open (POS, unpaid)"),
        ("settled", "Settled (POS, paid)"),
        ("refunded", "Refunded (POS)"),
    ]
    WEB_STATUSES = ("pending", "confirmed", "preparing", "out_for_delivery", "delivered", "cancelled")

    SOURCE_CHOICES = [("web", "Website"), ("pos", "POS terminal")]
    ORDER_TYPE_CHOICES = [
        ("online", "Online"), ("counter", "Counter"),
        ("dine_in", "Dine In"), ("takeaway", "Takeaway"),
    ]

    # Website orders must fill name/mobile/address (the web serializer enforces it);
    # a counter sale rung up at the POS has none of them.
    full_name = models.CharField(max_length=150, blank=True)
    mobile_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    alt_phone = models.CharField(max_length=20, blank=True)
    address_line = models.TextField(blank=True)

    # Where the order came from, and (for POS sales) the till details.
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="web")
    client_order_id = models.UUIDField(null=True, blank=True, unique=True)  # makes a retried POS sync safe
    shift = models.ForeignKey("pos.Shift", null=True, blank=True, on_delete=models.SET_NULL, related_name="cor_orders")
    order_type = models.CharField(max_length=10, choices=ORDER_TYPE_CHOICES, default="online")
    table_label = models.CharField(max_length=40, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    special_instructions = models.TextField(blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default="cod")

    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_charges = models.DecimalField(max_digits=10, decimal_places=2, default=250)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    status_changed_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.CharField(max_length=255, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    settled_at = models.DateTimeField(null=True, blank=True)

    customer = models.ForeignKey(
        "accounts.Customer", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="cor_orders",
    )
    placed_by_account = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Cor order #{self.id} - {self.full_name or self.get_order_type_display()}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    # Snapshot of what the customer was charged - never changes.
    item_name = models.CharField(max_length=150)
    size_label = models.CharField(max_length=40, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)
    # Links back to the live menu, for reports.
    menu_item = models.ForeignKey(MenuItem, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    price = models.ForeignKey(MenuItemPrice, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    deal = models.ForeignKey(Deal, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    def __str__(self):
        return f"{self.quantity} x {self.item_name}"


class Settlement(models.Model):
    """The payment taken for a POS order."""
    PAYMENT_CHOICES = [("cash", "Cash"), ("card", "Card")]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="settlement")
    cashier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="cor_settlements")
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES)
    amount_tendered = models.DecimalField(max_digits=10, decimal_places=2)
    change_due = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    settled_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Settlement for Cor order #{self.order_id}"


class Refund(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="refund")
    cashier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="cor_refunds")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255, blank=True)
    refunded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Refund for Cor order #{self.order_id}"
