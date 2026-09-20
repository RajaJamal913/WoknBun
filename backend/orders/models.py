from django.db import models


class Order(models.Model):
    PAYMENT_CHOICES = [
        ("cod", "Cash On Delivery"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("preparing", "Preparing"),
        ("out_for_delivery", "Out For Delivery"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]

    full_name = models.CharField(max_length=150)
    mobile_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    alt_phone = models.CharField(max_length=20, blank=True)
    address_line = models.TextField()
    special_instructions = models.TextField(blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default="cod")

    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_charges = models.DecimalField(max_digits=10, decimal_places=2, default=250)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.id} - {self.full_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    item_name = models.CharField(max_length=150)
    size_label = models.CharField(max_length=40, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.item_name}"
