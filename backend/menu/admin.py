from django.contrib import admin
from .models import Category, MenuItem, MenuItemPrice, Deal


class MenuItemPriceInline(admin.TabularInline):
    model = MenuItemPrice
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "badge", "is_active", "order")
    list_filter = ("category", "badge", "is_active")
    search_fields = ("name", "description")
    inlines = [MenuItemPriceInline]


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "is_active", "order")
    list_filter = ("is_active",)
