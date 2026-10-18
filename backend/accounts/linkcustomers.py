from django.core.management.base import BaseCommand

from accounts.services import find_or_create_customer
from orders.models import Order as WebOrder
from pos.models import Order as Sale


class Command(BaseCommand):
    help = ("Create customer records from existing website orders (matched by phone number) and link each "
            "order, and its POS sale, to its customer. Safe to run again - it only touches unlinked orders.")

    def handle(self, *args, **options):
        linked = skipped = 0
        # Oldest first, so a customer's name comes from their FIRST order.
        for order in WebOrder.objects.filter(customer__isnull=True).order_by("id"):
            customer = find_or_create_customer(order.full_name, order.mobile_number, order.email, order.alt_phone)
            if customer is None:
                skipped += 1
                self.stdout.write(self.style.WARNING(f"  order #{order.id}: '{order.mobile_number}' is not a usable phone number - left unlinked"))
                continue
            order.customer = customer
            order.save(update_fields=["customer"])
            Sale.objects.filter(online_order=order, customer__isnull=True).update(customer=customer)
            linked += 1
        # Sales made by older code may be missing their customer link even when the website order has one.
        repaired = 0
        for sale in Sale.objects.filter(online_order__isnull=False, customer__isnull=True).select_related("online_order"):
            if sale.online_order.customer_id:
                sale.customer_id = sale.online_order.customer_id
                sale.save(update_fields=["customer"])
                repaired += 1
        from accounts.models import Customer
        self.stdout.write(self.style.SUCCESS(
            f"Linked {linked} website order(s); {skipped} skipped; repaired {repaired} sale(s); {Customer.objects.count()} customer(s) in total."))