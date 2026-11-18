from django.core.management.base import BaseCommand
from django.db import transaction

from cor.menu_data import populate
from cor.models import Category, Deal, MenuItem, MenuItemPrice


class Command(BaseCommand):
    help = "Re-load the Cor menu (categories, items, prices, deals). Replaces Cor's menu only; its orders are kept."

    @transaction.atomic
    def handle(self, *args, **options):
        MenuItemPrice.objects.all().delete()
        MenuItem.objects.all().delete()
        Deal.objects.all().delete()
        Category.objects.all().delete()
        populate(Category, MenuItem, MenuItemPrice, Deal)
        self.stdout.write(self.style.SUCCESS(
            f"Cor: loaded {Category.objects.count()} categories, "
            f"{MenuItem.objects.count()} items, {Deal.objects.count()} deals."
        ))
