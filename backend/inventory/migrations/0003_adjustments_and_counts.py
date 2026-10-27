import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("inventory", "0002_recipes_and_deals"),
    ]

    operations = [
        migrations.AddField(
            model_name="stockmovement",
            name="client_ref",
            field=models.UUIDField(
                blank=True,
                help_text="Set on manual adjustments so a retry is saved once",
                null=True,
                unique=True,
            ),
        ),
        migrations.CreateModel(
            name="StockCount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("client_ref", models.UUIDField(blank=True, null=True, unique=True)),
                ("note", models.CharField(blank=True, max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.CreateModel(
            name="StockCountLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "expected",
                    models.DecimalField(decimal_places=3, help_text="What the system said, in stock units", max_digits=14),
                ),
                ("counted", models.DecimalField(decimal_places=3, max_digits=14)),
                (
                    "difference",
                    models.DecimalField(decimal_places=3, help_text="counted - expected", max_digits=14),
                ),
                (
                    "unit_cost",
                    models.DecimalField(
                        blank=True,
                        decimal_places=4,
                        help_text="Per stock unit, last known",
                        max_digits=14,
                        null=True,
                    ),
                ),
                (
                    "count",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lines",
                        to="inventory.stockcount",
                    ),
                ),
                (
                    "material",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="inventory.rawmaterial",
                    ),
                ),
            ],
        ),
    ]
