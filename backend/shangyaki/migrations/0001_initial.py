import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0002_remove_customer_auth_token_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("slug", models.SlugField(blank=True, max_length=110, unique=True)),
                ("order", models.PositiveIntegerField(default=0)),
            ],
            options={"verbose_name_plural": "Categories", "ordering": ["order", "name"]},
        ),
        migrations.CreateModel(
            name="Deal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                ("description", models.TextField(help_text="One line per item, e.g. '2 Chicken Burgers'")),
                ("price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("badge", models.CharField(blank=True, help_text="e.g. '2 Mint Margarita Complimentary'", max_length=100)),
                ("image_url", models.URLField(blank=True)),
                ("order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["order", "id"]},
        ),
        migrations.CreateModel(
            name="MenuItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("note", models.CharField(blank=True, help_text="Small print shown under the item", max_length=255)),
                ("image_url", models.URLField(blank=True)),
                ("badge", models.CharField(blank=True, choices=[("", "None"), ("best_seller", "Best Seller"), ("new", "New")], max_length=20)),
                ("order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="shangyaki.category")),
            ],
            options={"ordering": ["order", "name"]},
        ),
        migrations.CreateModel(
            name="MenuItemPrice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(blank=True, max_length=40)),
                ("price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("order", models.PositiveIntegerField(default=0)),
                ("menu_item", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="prices", to="shangyaki.menuitem")),
            ],
            options={"ordering": ["order", "id"]},
        ),
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("full_name", models.CharField(max_length=150)),
                ("mobile_number", models.CharField(max_length=20)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("alt_phone", models.CharField(blank=True, max_length=20)),
                ("address_line", models.TextField()),
                ("special_instructions", models.TextField(blank=True)),
                ("payment_method", models.CharField(choices=[("cod", "Cash On Delivery")], default="cod", max_length=20)),
                ("subtotal", models.DecimalField(decimal_places=2, max_digits=10)),
                ("delivery_charges", models.DecimalField(decimal_places=2, default=250, max_digits=10)),
                ("tax_amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("grand_total", models.DecimalField(decimal_places=2, max_digits=10)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("confirmed", "Confirmed"), ("preparing", "Preparing"), ("out_for_delivery", "Out For Delivery"), ("delivered", "Delivered"), ("cancelled", "Cancelled")], default="pending", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("status_changed_at", models.DateTimeField(blank=True, null=True)),
                ("cancel_reason", models.CharField(blank=True, max_length=255)),
                ("placed_by_account", models.BooleanField(default=False)),
                ("customer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="shangyaki_orders", to="accounts.customer")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="OrderItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("item_name", models.CharField(max_length=150)),
                ("size_label", models.CharField(blank=True, max_length=40)),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("line_total", models.DecimalField(decimal_places=2, max_digits=10)),
                ("deal", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="shangyaki.deal")),
                ("menu_item", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="shangyaki.menuitem")),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="shangyaki.order")),
                ("price", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="shangyaki.menuitemprice")),
            ],
        ),
    ]
