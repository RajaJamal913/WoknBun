from django.contrib import admin

from .models import Category, Deal, MenuItem, MenuItemPrice, Order, OrderItem, Refund, Settlement


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


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("item_name", "size_label", "unit_price", "quantity", "line_total")
    can_delete = False


class SettlementInline(admin.StackedInline):
    model = Settlement
    extra = 0
    can_delete = False
    readonly_fields = ("cashier", "payment_method", "amount_tendered", "change_due", "settled_at")


class RefundInline(admin.StackedInline):
    model = Refund
    extra = 0
    can_delete = False
    readonly_fields = ("cashier", "amount", "reason", "refunded_at")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "source", "order_type", "full_name", "mobile_number", "grand_total", "status", "created_at")
    list_filter = ("source", "order_type", "status", "payment_method")
    search_fields = ("full_name", "mobile_number", "email")
    inlines = [OrderItemInline, SettlementInline, RefundInline]
    readonly_fields = ("subtotal", "discount_amount", "delivery_charges", "tax_amount", "grand_total", "created_at")
