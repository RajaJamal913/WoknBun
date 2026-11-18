import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cor", "0001_initial"),
        ("pos", "0005_order_customer"),
    ]

    operations = [
        migrations.AlterField(model_name="order", name="full_name", field=models.CharField(blank=True, max_length=150)),
        migrations.AlterField(model_name="order", name="mobile_number", field=models.CharField(blank=True, max_length=20)),
        migrations.AlterField(model_name="order", name="address_line", field=models.TextField(blank=True)),
        migrations.AddField(model_name="order", name="source", field=models.CharField(choices=[("web", "Website"), ("pos", "POS terminal")], default="web", max_length=10)),
        migrations.AddField(model_name="order", name="client_order_id", field=models.UUIDField(blank=True, null=True, unique=True)),
        migrations.AddField(model_name="order", name="shift", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="cor_orders", to="pos.shift")),
        migrations.AddField(model_name="order", name="order_type", field=models.CharField(choices=[("online", "Online"), ("counter", "Counter"), ("dine_in", "Dine In"), ("takeaway", "Takeaway")], default="online", max_length=10)),
        migrations.AddField(model_name="order", name="table_label", field=models.CharField(blank=True, max_length=40)),
        migrations.AddField(model_name="order", name="discount_amount", field=models.DecimalField(decimal_places=2, default=0, max_digits=10)),
    ]
