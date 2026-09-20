from django.db import models
from django.utils.text import slugify


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
    note = models.CharField(
        max_length=255,
        blank=True,
        help_text="Small print shown under the item, e.g. 'All burgers are served with fries'",
    )
    image_url = models.URLField(blank=True)
    badge = models.CharField(max_length=20, choices=BADGE_CHOICES, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name} ({self.category.name})"


class MenuItemPrice(models.Model):
    """
    A single item can have one price (label left blank) or several
    size/variant prices, e.g. Single/Double or Small/Medium/Large/X-Large.
    """
    menu_item = models.ForeignKey(MenuItem, related_name="prices", on_delete=models.CASCADE)
    label = models.CharField(max_length=40, blank=True, help_text="e.g. Single, Double, Small, Large")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        label = self.label or "Price"
        return f"{self.menu_item.name} - {label}: Rs. {self.price}"


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
