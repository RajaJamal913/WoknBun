from django.contrib import admin

from .models import (DealComponent, PurchaseInvoice, PurchaseInvoiceLine, PurchasePayment, RawMaterial, RecipeLine,
                     StockMovement, Supplier, Warehouse)

admin.site.register(Warehouse)
admin.site.register(Supplier)


@admin.register(RawMaterial)
class RawMaterialAdmin(admin.ModelAdmin):
    list_display = ("name", "stock_unit", "purchase_unit", "purchase_factor", "reorder_level", "is_active")
    search_fields = ("name",)


class LineInline(admin.TabularInline):
    model = PurchaseInvoiceLine
    extra = 0
    can_delete = False
    readonly_fields = ("material", "quantity", "unit_price", "line_total", "purchase_unit", "stock_quantity")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "supplier", "invoice_number", "invoice_date", "total", "amount_paid", "status")
    list_filter = ("status",)
    inlines = [LineInline]
    # Posted bills are corrected by voiding them in the POS, never by editing here: the ledger must stay true.
    readonly_fields = [f.name for f in PurchaseInvoice._meta.fields]


admin.site.register(PurchasePayment)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("created_at", "material", "quantity", "movement_type", "reference_type", "reference_id")
    list_filter = ("movement_type", "material")
    readonly_fields = [f.name for f in StockMovement._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(RecipeLine)
admin.site.register(DealComponent)
