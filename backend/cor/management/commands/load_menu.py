from django.core.management.base import BaseCommand
from django.db import transaction

from cor.models import Category, Deal, MenuItem, MenuItemPrice

# Transcribed from the Cor printed menu (DHA Phase II, Islamabad).

WING_NOTE = "Any sauce of your choice among Dynamite, Buffalo, Hot Honey & BBQ"
PIZZA_SIZES = {"Small": 649, "Medium": 1299, "Large": 1999, "X-Large": 2599}

# (category, category-wide note, items)
MENU = [
    ("Appetizers", "", [
        {"name": "Chicken Wings (6 pcs)", "note": WING_NOTE, "price": 749},
        {"name": "Chicken Tender (3 pcs)", "note": WING_NOTE, "price": 999},
        {"name": "Plain Fries (200g)", "price": 399},
        {"name": "Animal Fries (300g)", "price": 749},
        {"name": "Chicken Dumplings (6 pcs)", "price": 749},
        {"name": "Hot & Sour Soup", "price": 599},
        {"name": "Corn Soup", "price": 599},
        {"name": "Thai Soup", "price": 599},
        {"name": "Special Soup", "price": 899},
    ]),
    ("Gourmet Beef Burgers", "All burgers are served with fries", [
        {"name": "Classic Smash", "sizes": {"Single": 749, "Double": 999}},
        {"name": "Swiss Mushroom", "sizes": {"Single": 799, "Double": 1099}},
        {"name": "Sweet & Smoky BBQ", "sizes": {"Single": 899, "Double": 1199}},
        {"name": "Spicy Jalape\u00f1o", "sizes": {"Single": 799, "Double": 1099}},
        {"name": "Grilled Special", "sizes": {"Single": 899, "Double": 1199}},
    ]),
    ("Chicken Burgers", "", [
        {"name": "Ultimate Crispy Burger", "price": 599},
        {"name": "Jalape\u00f1o Popper Burger", "price": 799},
        {"name": "BBQ Crunch Burger", "price": 749},
        {"name": "Grilled Swiss Mushroom Burger", "price": 749},
    ]),
    ("Wraps", "", [
        {"name": "Zing Wing Wrap", "price": 649},
        {"name": "Mexican Wrap", "price": 649},
        {"name": "Special Loaded Wrap", "price": 749},
    ]),
    ("Pizza", "", [
        {"name": "Chicken Tikka", "sizes": PIZZA_SIZES},
        {"name": "Chicken Fajita", "sizes": PIZZA_SIZES},
        {"name": "Chicken Cheese Lover", "sizes": PIZZA_SIZES},
        {"name": "Chicken Supreme", "sizes": PIZZA_SIZES},
        {"name": "Beef Pepperoni", "sizes": {"Small": 699, "Medium": 1349, "Large": 2099, "X-Large": 2699}},
        {"name": "Crown Crust", "sizes": {"Large": 2399, "X-Large": 2999}},
    ]),
    ("Pasta", "", [
        {"name": "Mac & Cheese Creamy Pasta", "price": 999},
        {"name": "Chicken Alfredo Pasta", "price": 1299},
        {"name": "Pasta Lavista", "price": 1299},
        {"name": "Special Pasta", "price": 1499},
    ]),
    ("Seafood", "", [
        {"name": "Fish & Chips", "price": 1299},
        {"name": "Dynamite Prawns", "price": 1499},
        {"name": "Prawn Tempura", "price": 1599},
    ]),
    ("Sides", "", [
        {"name": "Chicken Nuggets (6 pcs)", "price": 599},
        {"name": "Onion Rings (10 pcs)", "price": 499},
        {"name": "Coleslaw", "price": 299},
    ]),
    ("Beverages", "", [
        {"name": "Cola Next / Pepsi", "sizes": {"345 ml": 130, "500 ml": 150}},
        {"name": "Mint Margarita", "price": 299},
        {"name": "Mineral Water", "sizes": {"Small": 120, "Large": 199}},
    ]),
]

DEALS = [
    {"name": "Any 2 Pastas Deal", "description": "Any 2 Pastas of your choice", "price": 1799},
    {"name": "Student Deal", "description": "Any Chicken Burger\nRegular Fries\nSoft Drink 345ml", "price": 999},
    {"name": "Burger Deal (2 Persons)", "description": "2 Chicken Burgers\n1 Large Fries\n2 Soft Drinks 345ml", "price": 1599},
    {"name": "Smash Lovers Deal", "description": "2 Smash Burgers\n1 Animal Fries\n2 Soft Drinks 345ml", "price": 2299},
    {"name": "Pizza Deal 1", "description": "1 Medium Pizza\n2 Zinger Burgers\n1 Soft Drink 500ml", "price": 2399},
    {"name": "Pizza Deal 2", "description": "1 Large Pizza\n6 Chicken Wings\n1 Soft Drink 1 Ltr", "price": 2599},
    {"name": "Family Pizza Deal", "description": "2 Large Pizzas\n1 Loaded Fries\n6 Chicken Wings\nSoft Drink 1.5 Ltr", "price": 3999},
]


class Command(BaseCommand):
    help = "Load the Cor menu (categories, items, prices, deals). Replaces this restaurant's existing menu only."

    @transaction.atomic
    def handle(self, *args, **options):
        MenuItemPrice.objects.all().delete()
        MenuItem.objects.all().delete()
        Deal.objects.all().delete()
        Category.objects.all().delete()

        for ci, (cat_name, note, items) in enumerate(MENU):
            category = Category.objects.create(name=cat_name, order=ci)
            for i, item in enumerate(items):
                mi = MenuItem.objects.create(
                    category=category, name=item["name"],
                    note=item.get("note", note), badge=item.get("badge", ""), order=i,
                )
                if "sizes" in item:
                    for j, (label, price) in enumerate(item["sizes"].items()):
                        MenuItemPrice.objects.create(menu_item=mi, label=label, price=price, order=j)
                else:
                    MenuItemPrice.objects.create(menu_item=mi, label="", price=item["price"], order=0)

        for i, d in enumerate(DEALS):
            Deal.objects.create(
                name=d["name"], description=d["description"], price=d["price"],
                badge=d.get("badge", ""), order=i,
            )

        self.stdout.write(self.style.SUCCESS(
            f"Cor: loaded {Category.objects.count()} categories, "
            f"{MenuItem.objects.count()} items, {Deal.objects.count()} deals."
        ))
