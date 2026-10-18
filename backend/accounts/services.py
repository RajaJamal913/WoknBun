from django.db import IntegrityError, transaction

from .models import Customer
from .phone import normalize_phone


def find_or_create_customer(full_name, phone_raw, email="", alt_phone=""):
    """
    The customer with this phone number - created if new. Returns None when the
    number isn't usable (the order still goes through, just unlinked).

    A returning customer's record is only ever FILLED IN (a missing email, say),
    never overwritten: people spell their name differently each time, and staff
    can correct details on the Customers screen.
    """
    phone = normalize_phone(phone_raw)
    if not phone:
        return None
    name = (full_name or "").strip()[:150]
    email = (email or "").strip()[:254]
    alt = (alt_phone or "").strip()[:20]

    try:
        with transaction.atomic():
            customer, created = Customer.objects.get_or_create(
                phone=phone, defaults={"full_name": name or "Customer", "email": email, "alt_phone": alt})
    except IntegrityError:  # two orders from a brand-new customer raced; the other one won
        customer, created = Customer.objects.get(phone=phone), False

    if not created:
        changed = []
        if name and not customer.full_name.strip():
            customer.full_name = name; changed.append("full_name")
        if email and not customer.email:
            customer.email = email; changed.append("email")
        if alt and not customer.alt_phone:
            customer.alt_phone = alt; changed.append("alt_phone")
        if changed:
            customer.save(update_fields=changed)
    return customer