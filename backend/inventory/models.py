"""
Inventory: raw materials, suppliers, purchase invoices and the stock ledger.

The ONE rule that keeps stock honest: quantities are never stored and edited. Every change
(opening stock, a purchase, a void, later a sale or an adjustment) is a row in StockMovement,
and "stock on hand" is simply the sum of a material's movements. Rows are only ever added.

Stock is counted in the material's STOCK unit (the small one used in recipes, e.g. grams).
Invoices are entered in its PURCHASE unit (the big one you buy, e.g. kg); purchase_factor
says how many stock units one purchase unit holds (1 kg = 1000 g).
"""
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models


class Warehouse(models.Model):
    """One today (the kitchen is the store room). A real table so a second location is not a migration."""
    name = models.CharField(max_length=100, unique=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.name


DEFAULT_WAREHOUSE_NAME = "Main Kitchen & Store"


def default_warehouse():
    wh = Warehouse.objects.filter(is_default=True).first()
    if wh is None:
        wh, _ = Warehouse.objects.get_or_create(name=DEFAULT_WAREHOUSE_NAME, defaults={"is_default": True})
    return wh


class RawMaterial(models.Model):
    name = models.CharField(max_length=150, unique=True)
    stock_unit = models.CharField(max_length=20, help_text="Unit stock is counted and used in, e.g. g, ml, pcs")
    purchase_unit = models.CharField(max_length=20, help_text="Unit you buy it in, e.g. kg, litre, carton")
    purchase_factor = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal("1"),
        help_text="How many stock units are in one purchase unit (1 kg = 1000 g)")
    reorder_level = models.DecimalField(
        max_digits=14, decimal_places=3, default=Decimal("0"),
        help_text="Flag as low when stock falls to this many stock units")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=150, unique=True)
    phone = models.CharField(max_length=30, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class PurchaseInvoice(models.Model):
    STATUS_CHOICES = [("posted", "Posted"), ("void", "Void")]

    # Sent by the screen so a double-click or a retry can never post the same bill twice.
    client_ref = models.UUIDField(unique=True, null=True, blank=True, default=uuid.uuid4)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="invoices")
    invoice_number = models.CharField(max_length=60, blank=True, help_text="The supplier's own bill number")
    invoice_date = models.DateField()
    notes = models.CharField(max_length=255, blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="posted")
    void_reason = models.CharField(max_length=255, blank=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-invoice_date", "-id"]

    @property
    def balance_due(self):
        return self.total - self.amount_paid

    def __str__(self):
        return f"Purchase #{self.id} - {self.supplier}"


class PurchaseInvoiceLine(models.Model):
    invoice = models.ForeignKey(PurchaseInvoice, related_name="lines", on_delete=models.CASCADE)
    material = models.ForeignKey(RawMaterial, on_delete=models.PROTECT, related_name="+")
    quantity = models.DecimalField(max_digits=14, decimal_places=3, help_text="In the purchase unit")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Per purchase unit")
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    # Snapshots, so changing a material later never rewrites an old bill.
    purchase_unit = models.CharField(max_length=20)
    stock_quantity = models.DecimalField(max_digits=14, decimal_places=3, help_text="quantity x factor, in stock units")


class PurchasePayment(models.Model):
    METHOD_CHOICES = [("cash", "Cash"), ("bank", "Bank / online")]

    invoice = models.ForeignKey(PurchaseInvoice, related_name="payments", on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES, default="cash")
    paid_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")


class StockMovement(models.Model):
    """The ledger. Append-only: a mistake is corrected by a new, opposite row, never by editing one."""
    TYPE_CHOICES = [
        ("opening", "Opening stock"),
        ("purchase", "Purchase"),
        ("purchase_void", "Purchase voided"),
        ("sale", "Used in a sale"),
        ("sale_reversal", "Sale reversed"),
        ("adjustment", "Adjustment"),
        ("wastage", "Wastage"),
        ("count", "Stock count"),
    ]

    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="movements")
    material = models.ForeignKey(RawMaterial, on_delete=models.PROTECT, related_name="movements")
    quantity = models.DecimalField(max_digits=14, decimal_places=3, help_text="Stock units; + in, - out")
    movement_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True, help_text="Per stock unit, when known")
    reference_type = models.CharField(max_length=30, blank=True)
    reference_id = models.PositiveIntegerField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["material", "created_at"])]

    def __str__(self):
        return f"{self.material} {self.quantity:+} ({self.movement_type})"


class RecipeLine(models.Model):
    """
    What ONE serving of a menu item (at one size/price) uses up. Quantity is in the material's
    STOCK unit (e.g. 120 g of chicken). One row per material per size; a size with no rows has no recipe yet.
    """
    price = models.ForeignKey("menu.MenuItemPrice", on_delete=models.CASCADE, related_name="recipe_lines")
    material = models.ForeignKey(RawMaterial, on_delete=models.PROTECT, related_name="recipe_lines")
    quantity = models.DecimalField(max_digits=12, decimal_places=3)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["price", "material"], name="uniq_recipe_price_material")]
        ordering = ["id"]

    def __str__(self):
        return f"{self.price_id}: {self.quantity} x {self.material}"


class DealComponent(models.Model):
    """One menu item (a size) that comes inside a deal, and how many of it. Stock for a deal is the sum of its components' recipes."""
    deal = models.ForeignKey("menu.Deal", on_delete=models.CASCADE, related_name="components")
    price = models.ForeignKey("menu.MenuItemPrice", on_delete=models.PROTECT, related_name="deal_components")
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["deal", "price"], name="uniq_deal_component")]
        ordering = ["id"]

    def __str__(self):
        return f"{self.deal_id}: {self.quantity} x price {self.price_id}"
