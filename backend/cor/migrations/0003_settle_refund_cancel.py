import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def open_pos_sales(apps, schema_editor):
    """The first POS version recorded sales as 'confirmed'. They have no payment yet, so they are 'open' now."""
    Order = apps.get_model("cor", "Order")
    Order.objects.filter(source="pos", status="confirmed").update(status="open")


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("cor", "0002_pos_orders"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order", name="status",
            field=models.CharField(
                choices=[("pending", "Pending"), ("confirmed", "Confirmed"), ("preparing", "Preparing"),
                         ("out_for_delivery", "Out For Delivery"), ("delivered", "Delivered"), ("cancelled", "Cancelled"),
                         ("open", "Open (POS, unpaid)"), ("settled", "Settled (POS, paid)"), ("refunded", "Refunded (POS)")],
                default="pending", max_length=20),
        ),
        migrations.AddField(model_name="order", name="cancelled_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="order", name="settled_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.CreateModel(
            name="Settlement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("payment_method", models.CharField(choices=[("cash", "Cash"), ("card", "Card")], max_length=10)),
                ("amount_tendered", models.DecimalField(decimal_places=2, max_digits=10)),
                ("change_due", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("settled_at", models.DateTimeField(auto_now_add=True)),
                ("cashier", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cor_settlements", to=settings.AUTH_USER_MODEL)),
                ("order", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="settlement", to="cor.order")),
            ],
        ),
        migrations.CreateModel(
            name="Refund",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("reason", models.CharField(blank=True, max_length=255)),
                ("refunded_at", models.DateTimeField(auto_now_add=True)),
                ("cashier", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cor_refunds", to=settings.AUTH_USER_MODEL)),
                ("order", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="refund", to="cor.order")),
            ],
        ),
        migrations.RunPython(open_pos_sales, migrations.RunPython.noop),
    ]
