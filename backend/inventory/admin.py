import os

from django.contrib import admin, messages
from django.db import transaction

from .models import (DealComponent, PurchaseInvoice, PurchaseInvoiceLine, PurchasePayment, RawMaterial, RecipeLine,
                     StockCountLine, StockMovement, Supplier, Warehouse)

admin.site.register(Warehouse)
admin.site.register(Supplier)


def is_unused(material):
    """True only for an ingredient created by mistake: its sole history is the opening stock typed in when it was
    added, and no bill, recipe or count refers to it. Anything with real history must be retired, not erased."""
    return (not material.movements.exclude(movement_type="opening").exists()
            and not PurchaseInvoiceLine.objects.filter(material=material).exists()
            and not RecipeLine.objects.filter(material=material).exists()
            and not StockCountLine.objects.filter(material=material).exists())


@admin.register(RawMaterial)
class RawMaterialAdmin(admin.ModelAdmin):
    list_display = ("name", "stock_unit", "purchase_unit", "purchase_factor", "reorder_level", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    actions = ["delete_mistakes", "retire"]

    @admin.action(description="Delete ingredients added by mistake (only if never used)")
    def delete_mistakes(self, request, queryset):
        deleted, kept = [], []
        with transaction.atomic():
            for m in queryset:
                if is_unused(m):
                    m.movements.all().delete()      # just its opening-stock row(s)
                    m.delete()
                    deleted.append(m.name)
                else:
                    kept.append(m.name)
        if deleted:
            self.message_user(request, f"Deleted: {', '.join(deleted)}.", messages.SUCCESS)
        if kept:
            self.message_user(request, f"Not deleted, because they have stock history, bills or recipes: {', '.join(kept)}. "
                                       "Use \"Retire\" to hide them instead.", messages.WARNING)

    @admin.action(description="Retire selected ingredients (hide them, keep their history)")
    def retire(self, request, queryset):
        n = queryset.update(is_active=False)
        self.message_user(request, f"Retired {n} ingredient(s). They no longer show in Stock, and their history is kept.", messages.SUCCESS)


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
        # Locked by default: the ledger is the proof of what happened. While you are still clearing out TEST data,
        # put INVENTORY_ALLOW_LEDGER_DELETE=1 in backend/.env to let a superuser delete rows here. Remove it again
        # before real trading starts.
        return os.environ.get("INVENTORY_ALLOW_LEDGER_DELETE") == "1" and request.user.is_superuser


admin.site.register(RecipeLine)
admin.site.register(DealComponent)
