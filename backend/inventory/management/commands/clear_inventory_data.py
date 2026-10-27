from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from inventory.models import (PurchaseInvoice, PurchaseInvoiceLine, PurchasePayment, RawMaterial, RecipeLine, StockCount,
                              StockCountLine, StockMovement, Supplier)

# Children first, because most links are PROTECT.
ORDER = [StockCountLine, StockCount, PurchasePayment, PurchaseInvoiceLine, PurchaseInvoice, StockMovement, RecipeLine,
         RawMaterial, Supplier]


class Command(BaseCommand):
    help = ("Erase ALL inventory data: ingredients, stock history, bills, payments, counts, recipes and suppliers. "
            "For clearing test data only. Menu items, orders and users are not touched.")

    def add_arguments(self, parser):
        parser.add_argument("--yes", action="store_true", help="Do not ask for confirmation")

    def handle(self, *args, **opts):
        counts = {m.__name__: m.objects.count() for m in ORDER}
        self.stdout.write("This will permanently delete:")
        for name, n in counts.items():
            self.stdout.write(f"  {name}: {n}")
        if not opts["yes"]:
            if input("Type DELETE to continue: ").strip() != "DELETE":
                raise CommandError("Cancelled. Nothing was deleted.")
        with transaction.atomic():
            for model in ORDER:
                model.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("Inventory data cleared."))
