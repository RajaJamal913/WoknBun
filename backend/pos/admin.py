from django.contrib import admin
from .models import StaffProfile, Shift, Order, OrderItem, Settlement, Refund


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("item_name", "size_label", "unit_price", "quantity", "line_total")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "shift", "status", "grand_total", "created_at")
    list_filter = ("status", "order_type")
    inlines = [OrderItemInline]


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ("id", "cashier", "status", "opening_cash", "closing_cash", "opened_at", "closed_at")


admin.site.register(Settlement)
admin.site.register(Refund)