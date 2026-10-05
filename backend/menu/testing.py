"""Shared fixtures for tests in other apps."""
from decimal import Decimal

from django.core.cache import cache
from menu.models import Category, Deal, MenuItem, MenuItemPrice


def make_menu():
    cat = Category.objects.create(name="Pizza")
    pizza = MenuItem.objects.create(category=cat, name="Fajita Pizza")
    small = MenuItemPrice.objects.create(menu_item=pizza, label="Small", price=Decimal("649"))
    large = MenuItemPrice.objects.create(menu_item=pizza, label="Large", price=Decimal("1999"))
    fries = MenuItem.objects.create(category=cat, name="Fries")
    fries_price = MenuItemPrice.objects.create(menu_item=fries, label="", price=Decimal("399"))
    hidden = MenuItem.objects.create(category=cat, name="Retired", is_active=False)
    hidden_price = MenuItemPrice.objects.create(menu_item=hidden, label="", price=Decimal("100"))
    deal = Deal.objects.create(name="Student Deal", description="Burger\nFries", price=Decimal("999"))
    return dict(small=small, large=large, fries=fries_price, hidden=hidden_price, deal=deal, pizza=pizza)


def reset_throttles():
    cache.clear()
