from django.db import migrations

from shangyaki.menu_data import populate


def load_menu(apps, schema_editor):
    """Fill in the Shangyaki menu so it is there as soon as you run migrate."""
    Category = apps.get_model("shangyaki", "Category")
    MenuItem = apps.get_model("shangyaki", "MenuItem")
    MenuItemPrice = apps.get_model("shangyaki", "MenuItemPrice")
    Deal = apps.get_model("shangyaki", "Deal")
    if Category.objects.exists() or Deal.objects.exists():
        return  # a menu is already there (maybe edited in the admin) - never overwrite it
    populate(Category, MenuItem, MenuItemPrice, Deal)


class Migration(migrations.Migration):

    dependencies = [("shangyaki", "0003_settle_refund_cancel")]

    operations = [migrations.RunPython(load_menu, migrations.RunPython.noop)]
