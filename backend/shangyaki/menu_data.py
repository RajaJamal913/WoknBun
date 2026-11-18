"""The Shangyaki menu, transcribed from the printed menu (DHA Phase II, Islamabad).

Used by the data migration (fills the menu when you run `migrate`) and by the
`load_shangyaki_menu` command (re-loads it any time).
"""
from django.utils.text import slugify

REG_LARGE_1199 = {"Regular": 1199, "Large": 1999}
REG_LARGE_BEEF = {"Regular": 1499, "Large": 2299}

# (category, category-wide note, items)
MENU = [
    ("Appetizers", "", [
        {"name": "Chicken Dumplings (Pan Fried / Steam)", "price": 749},
        {"name": "Chicken Wings", "price": 749},
        {"name": "Dynamite Prawns", "price": 1499},
        {"name": "Hot and Sour Soup", "price": 599},
        {"name": "Corn Soup", "price": 599},
        {"name": "Thai Soup", "price": 599},
        {"name": "Shangyaki Special Soup", "price": 899},
    ]),
    ("Main Course", "", [
        {"name": "Chicken Chilli Dry", "sizes": REG_LARGE_1199},
        {"name": "Beef Chilli Dry", "sizes": REG_LARGE_BEEF},
        {"name": "Chicken Manchurian", "sizes": REG_LARGE_1199},
        {"name": "Chicken Schezwan", "sizes": REG_LARGE_1199},
        {"name": "Dragon Chicken", "sizes": REG_LARGE_1199},
        {"name": "Kung Pao Beef", "sizes": REG_LARGE_BEEF},
        {"name": "Kung Pao Chicken", "sizes": {"Regular": 1299, "Large": 1999}},
        {"name": "Mongolian Beef", "sizes": REG_LARGE_BEEF},
        {"name": "Cashew Nut Chicken", "sizes": {"Regular": 1399, "Large": 1999}},
        {"name": "Fish Chilli Dry", "sizes": REG_LARGE_BEEF},
        {"name": "Prawn Chilli Dry", "sizes": {"Regular": 1599, "Large": 2299}},
    ]),
    ("Fried Rice", "", [
        {"name": "Vegetable Fried Rice", "price": 649},
        {"name": "Chicken Fried Rice", "price": 749},
        {"name": "Egg Fried Rice", "price": 749},
        {"name": "Shangyaki Special Fried Rice", "price": 899},
    ]),
    ("Chow Mein", "", [
        {"name": "Vegetable Chow Mein", "price": 899},
        {"name": "Chicken Chow Mein", "price": 1099},
        {"name": "Shangyaki Special Chow Mein", "price": 1299},
    ]),
    ("Beverages", "", [
        {"name": "Cola Next / Pepsi", "sizes": {"345 ml": 130, "500 ml": 150}},
        {"name": "Mint Margarita", "price": 299},
        {"name": "Mineral Water", "sizes": {"Small": 120, "Large": 199}},
    ]),
]

DEALS = [
    {"name": "Chinese Deal 1", "description": "2 Chicken Gravy\nRice\nChow Mein", "price": 2899, "badge": "2 Mint Margarita Complimentary"},
    {"name": "Chinese Deal 2", "description": "2 Beef Gravy\nRice\nChow Mein", "price": 3299, "badge": "2 Mint Margarita Complimentary"},
    {"name": "Chinese Deal 3", "description": "1 Chicken Gravy\n1 Beef Gravy\nRice\nChow Mein", "price": 2999, "badge": "2 Mint Margarita Complimentary"},
    {"name": "Chinese Deal 4", "description": "Any Soup + Dumpling\n2 Full Gravy of Your Choice\nMenu + Chow Mein", "price": 4599, "badge": "4 Mint Margarita Complimentary"},
]


def populate(Category, MenuItem, MenuItemPrice, Deal):
    """Create every category, item, price and deal. Works with real or migration (historical) models."""
    for ci, (cat_name, note, items) in enumerate(MENU):
        category = Category.objects.create(name=cat_name, slug=slugify(cat_name), order=ci)
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
