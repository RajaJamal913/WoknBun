from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import PurchasePayment, RawMaterial, Supplier


def user_name(u):
    return (u.get_full_name() or u.get_username()) if u else ""


class MaterialSerializer(serializers.ModelSerializer):
    stock_on_hand = serializers.DecimalField(max_digits=16, decimal_places=3, read_only=True)
    opening_stock = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0"), write_only=True, required=False)

    class Meta:
        model = RawMaterial
        fields = ["id", "name", "stock_unit", "purchase_unit", "purchase_factor", "reorder_level", "is_active",
                  "stock_on_hand", "opening_stock"]
        extra_kwargs = {
            "purchase_factor": {"min_value": Decimal("0.001")},
            "reorder_level": {"min_value": Decimal("0")},
        }

    def validate_name(self, v):
        v = v.strip()
        if not v:
            raise serializers.ValidationError("Enter a name.")
        clash = RawMaterial.objects.filter(name__iexact=v)
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError("A material with this name already exists.")
        return v

    def validate_stock_unit(self, v):
        v = v.strip()
        if not v:
            raise serializers.ValidationError("Enter the unit.")
        # "500" or "1" is a quantity typed into the wrong box, not a unit; it would show up as "500 500" everywhere.
        if not any(ch.isalpha() for ch in v):
            raise serializers.ValidationError("Enter a unit such as g, kg, ml, litre or pcs (not a number).")
        return v

    validate_purchase_unit = validate_stock_unit

    def validate(self, attrs):
        # Stock is stored in the stock unit, so once stock has moved, renaming it (g -> kg) would silently
        # rewrite what every old number means. The one exception is repairing a unit that was never valid
        # (a number typed into the unit box): there is no real meaning to protect.
        # The purchase factor is NOT locked: every bill keeps its own converted quantity, so changing it only
        # affects future purchases.
        inst = self.instance
        if inst and "stock_unit" in attrs and attrs["stock_unit"] != inst.stock_unit and inst.movements.exists():
            if any(ch.isalpha() for ch in inst.stock_unit):
                raise serializers.ValidationError(
                    {"stock_unit": "The stock unit can't be changed once the material has stock history. Add a new material instead."})
        return attrs


class SupplierSerializer(serializers.ModelSerializer):
    balance_due = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Supplier
        fields = ["id", "name", "phone", "notes", "is_active", "balance_due"]

    def validate_name(self, v):
        v = v.strip()
        if not v:
            raise serializers.ValidationError("Enter a name.")
        clash = Supplier.objects.filter(name__iexact=v)
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError("A supplier with this name already exists.")
        return v


class PurchaseLineInput(serializers.Serializer):
    material = serializers.PrimaryKeyRelatedField(queryset=RawMaterial.objects.filter(is_active=True))
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0.001"))
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))


class PurchaseCreateSerializer(serializers.Serializer):
    client_ref = serializers.UUIDField(required=False, allow_null=True)
    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.filter(is_active=True))
    invoice_number = serializers.CharField(max_length=60, required=False, allow_blank=True)
    invoice_date = serializers.DateField(required=False)
    notes = serializers.CharField(max_length=255, required=False, allow_blank=True)
    paid_now = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False, default=Decimal("0"))
    payment_method = serializers.ChoiceField(choices=[c for c, _ in PurchasePayment.METHOD_CHOICES], required=False, default="cash")
    lines = PurchaseLineInput(many=True)

    def validate_lines(self, v):
        if not v:
            raise serializers.ValidationError("Add at least one item.")
        if len(v) > 100:
            raise serializers.ValidationError("An invoice can have at most 100 lines.")
        return v

    def validate_invoice_date(self, v):
        if v > timezone.localdate():
            raise serializers.ValidationError("The invoice date can't be in the future.")
        return v


class VoidSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255)

    def validate_reason(self, v):
        v = v.strip()
        if not v:
            raise serializers.ValidationError("Enter a reason for voiding this invoice.")
        return v


class PaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    method = serializers.ChoiceField(choices=[c for c, _ in PurchasePayment.METHOD_CHOICES], required=False, default="cash")


def invoice_row(inv):
    return {
        "id": inv.id, "supplier": inv.supplier_id, "supplier_name": inv.supplier.name, "invoice_number": inv.invoice_number,
        "invoice_date": inv.invoice_date.isoformat(), "total": str(inv.total), "amount_paid": str(inv.amount_paid),
        "balance_due": str(inv.balance_due) if inv.status == "posted" else "0.00",
        "status": inv.status, "created_at": inv.created_at.isoformat(),
    }


def invoice_detail(inv):
    body = invoice_row(inv)
    body.update({
        "notes": inv.notes, "void_reason": inv.void_reason,
        "voided_at": inv.voided_at.isoformat() if inv.voided_at else None,
        "created_by_name": user_name(inv.created_by),
        "lines": [{"material": l.material_id, "material_name": l.material.name, "quantity": str(l.quantity),
                   "purchase_unit": l.purchase_unit, "unit_price": str(l.unit_price), "line_total": str(l.line_total),
                   "stock_quantity": str(l.stock_quantity), "stock_unit": l.material.stock_unit} for l in inv.lines.select_related("material")],
        "payments": [{"amount": str(p.amount), "method": p.method, "paid_at": p.paid_at.isoformat(),
                      "by": user_name(p.created_by)} for p in inv.payments.select_related("created_by").order_by("id")],
    })
    return body
