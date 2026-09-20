from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("item_name", "size_label", "unit_price", "quantity", "line_total")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "mobile_number", "grand_total", "status", "created_at")
    list_filter = ("status", "payment_method")
    search_fields = ("full_name", "mobile_number", "email")
    inlines = [OrderItemInline]
    readonly_fields = ("subtotal", "delivery_charges", "tax_amount", "grand_total", "created_at")
