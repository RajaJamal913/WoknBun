from django.core.management.base import BaseCommand
from django.db import transaction
from menu.models import Category, MenuItem, MenuItemPrice, Deal

# All data below is transcribed from the Wok & Bun physical menu (DHA Phase II, Islamabad).

CATEGORIES = [
    "Appetizers", "Wraps", "Pizza", "Beef Burgers", "Chicken Burgers",
    "Pasta", "Seafood", "Fried Rice", "Chow Mein", "Main Course", "Beverages",
]

APPETIZERS = [
    {"name": "Chicken Wings (6 pcs)", "note": "Any sauce of your choice among Dynamite, Buffalo, Hot Honey & BBQ", "price": 749},
    {"name": "Nashville Tenders (3 pcs)", "badge": "best_seller", "price": 999},
    {"name": "Plain Fries", "price": 399},
    {"name": "Masalla Fries", "price": 499},
    {"name": "Loaded Fries", "price": 749},
    {"name": "Chicken Dumplings", "price": 699},
    {"name": "Hot & Sour Soup", "price": 549},
    {"name": "Corn Soup", "price": 549},
]

WRAPS = [
    {"name": "Zing Wing Wrap", "price": 649},
    {"name": "Mexican Wrap", "price": 649},
    {"name": "Special Loaded Wrap", "price": 749},
]

# label -> price per size
PIZZA = [
    {"name": "Chicken Tikka", "sizes": {"Small": 649, "Medium": 1299, "Large": 1999, "X-Large": 2599}},
    {"name": "Chicken Fajita", "sizes": {"Small": 649, "Medium": 1299, "Large": 1999, "X-Large": 2599}},
    {"name": "Chicken Cheese Lover", "sizes": {"Small": 649, "Medium": 1299, "Large": 1999, "X-Large": 2599}},
    {"name": "Chicken Supreme", "sizes": {"Small": 649, "Medium": 1299, "Large": 1999, "X-Large": 2599}},
    {"name": "Smokey Barbeque", "badge": "best_seller", "sizes": {"Small": 699, "Medium": 1349, "Large": 2099, "X-Large": 2699}},
    {"name": "Crown Crust", "sizes": {"Large": 2399, "X-Large": 2999}},
]

BEEF_BURGERS = [
    {"name": "Classic Smash", "sizes": {"Single": 749, "Double": 999}},
    {"name": "Swiss Mushroom", "sizes": {"Single": 799, "Double": 1099}},
    {"name": "Sweet & Smoky BBQ", "badge": "best_seller", "sizes": {"Single": 899, "Double": 1199}},
    {"name": "Spicy Jalapeño", "sizes": {"Single": 799, "Double": 1099}},
    {"name": "Grilled Special", "sizes": {"Single": 899, "Double": 1199}},
]
BEEF_BURGER_NOTE = "All burgers are served with fries"

CHICKEN_BURGERS = [
    {"name": "Nashville Burger", "badge": "best_seller", "price": 899},
    {"name": "Ultimate Crispy Burger", "price": 599},
    {"name": "Jalapeño Popper Burger", "price": 799},
    {"name": "BBQ Crunch Burger", "price": 749},
    {"name": "Grilled Swiss Mushroom Burger", "price": 749},
]

PASTA = [
    {"name": "Mac & Cheese Creamy Pasta", "price": 999},
    {"name": "Chicken Alfredo", "price": 1299},
    {"name": "Pasta Lavista", "price": 1299},
    {"name": "Special Pasta", "badge": "best_seller", "price": 1499},
]

SEAFOOD = [
    {"name": "Fish & Chips", "price": 1299},
    {"name": "Dynamite Prawns", "badge": "best_seller", "price": 1499},
    {"name": "Prawn Tempura", "price": 1599},
]

FRIED_RICE = [
    {"name": "Vegetable Fried Rice", "price": 649},
    {"name": "Chicken Fried Rice", "price": 749},
    {"name": "Egg Fried Rice", "price": 749},
    {"name": "Shangyaki Special Fried Rice", "badge": "best_seller", "price": 999},
]

CHOW_MEIN = [
    {"name": "Vegetable Chow Mein", "price": 899},
    {"name": "Chicken Chow Mein", "price": 1099},
    {"name": "Shangyaki Special Chow Mein", "badge": "best_seller", "price": 1299},
]

MAIN_COURSE = [
    {"name": "Chicken Chilli Dry", "sizes": {"Regular": 1199, "Large": 1999}},
    {"name": "Chicken Manchurian", "sizes": {"Regular": 1199, "Large": 1999}},
    {"name": "Chicken Schezwan", "sizes": {"Regular": 1199, "Large": 1999}},
    {"name": "Dragon Chicken", "badge": "best_seller", "sizes": {"Regular": 1199, "Large": 1999}},
    {"name": "Kung Pao Chicken", "sizes": {"Regular": 1299, "Large": 1999}},
    {"name": "Cashew Nut Chicken", "sizes": {"Regular": 1399, "Large": 1999}},
    {"name": "Black Pepper Chicken", "sizes": {"Regular": 1199, "Large": 1999}},
    {"name": "Chicken Garlic", "sizes": {"Regular": 1199, "Large": 1199}},
    {"name": "Kung Pao Beef", "sizes": {"Regular": 1499, "Large": 2299}},
    {"name": "Beef Chilli Dry", "sizes": {"Regular": 1499, "Large": 2299}},
    {"name": "Mongolian Beef", "badge": "best_seller", "sizes": {"Regular": 1499, "Large": 2299}},
]

BEVERAGES = [
    {"name": "Cola Next / Pepsi", "sizes": {"345 ml": 130, "500 ml": 150}},
    {"name": "Mint Margarita", "price": 299},
    {"name": "Mineral Water", "sizes": {"Small": 120, "Large": 199}},
]

DEALS = [
    {"name": "Student Deal", "description": "Any Chicken Burger\nRegular Fries\nSoft Drink 345ml", "price": 999},
    {"name": "Burger Deal (2 Persons)", "description": "2 Chicken Burgers\n1 Large Fries\n2 Soft Drinks 345ml", "price": 1599},
    {"name": "Smash Lovers Deal", "description": "2 Smash Burgers\n1 Animal Fries\n2 Soft Drinks 345ml", "price": 2299},
    {"name": "Pizza Deal 1", "description": "1 Medium Pizza\n2 Zinger Burgers\n1 Soft Drink 500ml", "price": 2399},
    {"name": "Pizza Deal 2", "description": "1 Large Pizza\n6 Chicken Wings\n1 Soft Drink 1 Ltr", "price": 2599},
    {"name": "Family Pizza Deal", "description": "2 Large Pizzas\n1 Loaded Fries\n6 Chicken Wings\nSoft Drink 1.5 Ltr", "price": 3999},
    {"name": "Chinese Deal 1", "description": "2 Chicken Gravy\nRice\nChow Mein", "price": 2899, "badge": "2 Mint Margarita Complimentary"},
    {"name": "Chinese Deal 2", "description": "2 Beef Gravy\nRice\nChow Mein", "price": 3299, "badge": "2 Mint Margarita Complimentary"},
    {"name": "Chinese Deal 3", "description": "1 Chicken Gravy\n1 Beef Gravy\nRice & Chow Mein", "price": 2999, "badge": "2 Mint Margarita Complimentary"},
    {"name": "Chinese Deal 4", "description": "Any Soup + Dumpling\n2 Full Gravy of Your Choice\nChow Mein", "price": 4599, "badge": "2 Mint Margarita Complimentary"},
]


class Command(BaseCommand):
    help = "Load the Wok & Bun menu (categories, items, prices, deals) into the database."

    @transaction.atomic
    def handle(self, *args, **options):
        MenuItemPrice.objects.all().delete()
        MenuItem.objects.all().delete()
        Deal.objects.all().delete()
        Category.objects.all().delete()

        cats = {}
        for i, name in enumerate(CATEGORIES):
            cats[name] = Category.objects.create(name=name, order=i)

        def add_items(category_name, items, note=""):
            category = cats[category_name]
            for i, item in enumerate(items):
                mi = MenuItem.objects.create(
                    category=category,
                    name=item["name"],
                    note=item.get("note", note),
                    badge=item.get("badge", ""),
                    order=i,
                )
                if "sizes" in item:
                    for j, (label, price) in enumerate(item["sizes"].items()):
                        MenuItemPrice.objects.create(menu_item=mi, label=label, price=price, order=j)
                else:
                    MenuItemPrice.objects.create(menu_item=mi, label="", price=item["price"], order=0)

        add_items("Appetizers", APPETIZERS)
        add_items("Wraps", WRAPS)
        add_items("Pizza", PIZZA)
        add_items("Beef Burgers", BEEF_BURGERS, note=BEEF_BURGER_NOTE)
        add_items("Chicken Burgers", CHICKEN_BURGERS)
        add_items("Pasta", PASTA)
        add_items("Seafood", SEAFOOD)
        add_items("Fried Rice", FRIED_RICE)
        add_items("Chow Mein", CHOW_MEIN)
        add_items("Main Course", MAIN_COURSE)
        add_items("Beverages", BEVERAGES)

        for i, deal in enumerate(DEALS):
            Deal.objects.create(
                name=deal["name"],
                description=deal["description"],
                price=deal["price"],
                badge=deal.get("badge", ""),
                order=i,
            )

        self.stdout.write(self.style.SUCCESS(
            f"Loaded {Category.objects.count()} categories, "
            f"{MenuItem.objects.count()} menu items, "
            f"{Deal.objects.count()} deals."
        ))
