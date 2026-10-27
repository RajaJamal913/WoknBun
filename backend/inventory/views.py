from datetime import timedelta

from django.db import IntegrityError
from django.db.models import DateTimeField, DecimalField, F, Max, Q, Sum
from django.db.models.functions import Coalesce
from django.http import Http404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from pos.permissions import IsManager
from pos.report_views import _date_param, _range
from menu.models import Deal, MenuItemPrice
from . import recipes, reports, services
from .models import PurchaseInvoice, RawMaterial, StockCount, Supplier
from .serializers import (AdjustmentSerializer, CountCreateSerializer, MaterialSerializer, PaymentSerializer,
                          PurchaseCreateSerializer, SupplierSerializer, VoidSerializer, count_detail, invoice_detail,
                          invoice_row)

ZERO = 0


def _materials():
    return RawMaterial.objects.annotate(
        stock_on_hand=Coalesce(Sum("movements__quantity"), ZERO, output_field=DecimalField()),
        last_purchased=Max("movements__created_at", filter=Q(movements__movement_type__in=["opening", "purchase"]),
                           output_field=DateTimeField()))


def _suppliers():
    return Supplier.objects.annotate(balance_due=Coalesce(
        Sum(F("invoices__total") - F("invoices__amount_paid"), filter=Q(invoices__status="posted")), ZERO,
        output_field=DecimalField()))


class MaterialListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsManager]
    serializer_class = MaterialSerializer
    pagination_class = None

    def get_queryset(self):
        qs = _materials()
        if self.request.query_params.get("active") == "1":
            qs = qs.filter(is_active=True)
        return qs

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        opening = ser.validated_data.pop("opening_stock", None)
        opening_date = ser.validated_data.pop("opening_date", None)
        material = services.create_material_with_opening(ser, request.user, opening, opening_date)
        return Response(MaterialSerializer(_materials().get(pk=material.pk)).data, status=status.HTTP_201_CREATED)


class MaterialDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsManager]
    serializer_class = MaterialSerializer
    queryset = RawMaterial.objects.all()
    http_method_names = ["get", "patch", "head", "options"]

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        ser = self.get_serializer(self.get_object(), data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.validated_data.pop("opening_stock", None)    # opening stock is entered once, when the material is created
        ser.validated_data.pop("opening_date", None)
        ser.save()
        return Response(MaterialSerializer(_materials().get(pk=ser.instance.pk)).data)


class SupplierListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsManager]
    serializer_class = SupplierSerializer
    pagination_class = None

    def get_queryset(self):
        qs = _suppliers()
        if self.request.query_params.get("active") == "1":
            qs = qs.filter(is_active=True)
        return qs

    def perform_create(self, serializer):
        serializer.save()


class SupplierDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsManager]
    serializer_class = SupplierSerializer
    queryset = Supplier.objects.all()
    http_method_names = ["get", "patch", "head", "options"]


def _invoice(pk):
    try:
        return PurchaseInvoice.objects.select_related("supplier", "created_by").get(pk=pk)
    except PurchaseInvoice.DoesNotExist:
        raise Http404("Invoice not found.")


class PurchaseInvoiceListCreateView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        qs = PurchaseInvoice.objects.select_related("supplier")
        supplier = request.query_params.get("supplier")
        if supplier and supplier.isdigit():
            qs = qs.filter(supplier_id=supplier)
        if request.query_params.get("due") == "1":
            qs = qs.filter(status="posted").filter(amount_paid__lt=F("total"))
        if request.query_params.get("from") or request.query_params.get("to"):
            d_from, d_to = _range(request)
            qs = qs.filter(invoice_date__gte=d_from, invoice_date__lte=d_to)
        return Response([invoice_row(i) for i in qs[:200]])

    def post(self, request):
        ser = PurchaseCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            invoice, created = services.post_purchase(request.user, ser.validated_data)
        except IntegrityError:    # the same client_ref arrived twice at once; the other one won
            invoice, created = PurchaseInvoice.objects.get(client_ref=ser.validated_data["client_ref"]), False
        return Response(invoice_detail(_invoice(invoice.pk)), status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class PurchaseInvoiceDetailView(APIView):
    permission_classes = [IsManager]

    def get(self, request, invoice_id):
        return Response(invoice_detail(_invoice(invoice_id)))


class PurchaseInvoiceVoidView(APIView):
    permission_classes = [IsManager]

    def post(self, request, invoice_id):
        ser = VoidSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        _invoice(invoice_id)
        try:
            services.void_purchase(request.user, invoice_id, ser.validated_data["reason"])
        except services.InventoryError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        invoice = _invoice(invoice_id)
        body = invoice_detail(invoice)
        if invoice.amount_paid > 0:
            body["warning"] = (f"Rs. {invoice.amount_paid} was already paid on this invoice. "
                               "Settle that with the supplier: the system does not refund it automatically.")
        return Response(body)


class PurchasePaymentView(APIView):
    permission_classes = [IsManager]

    def post(self, request, invoice_id):
        ser = PaymentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        _invoice(invoice_id)
        try:
            services.add_payment(request.user, invoice_id, ser.validated_data["amount"], ser.validated_data["method"])
        except services.InventoryError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(invoice_detail(_invoice(invoice_id)))


class StockSummaryView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        return Response(reports.stock_summary())


class StockLedgerView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        material_id = request.query_params.get("material", "")
        if not material_id.isdigit():
            return Response({"detail": "Choose a material."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            material = RawMaterial.objects.get(pk=material_id)
        except RawMaterial.DoesNotExist:
            raise Http404("Material not found.")
        return Response(reports.stock_ledger(material, *_range(request)))


class PurchaseReportView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        supplier = request.query_params.get("supplier", "")
        return Response(reports.purchase_report(*_range(request), supplier_id=int(supplier) if supplier.isdigit() else None))


class RecipeOverviewView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        return Response(recipes.overview())


class RecipeDetailView(APIView):
    """PUT replaces the whole recipe of one menu item size. An empty list clears it."""
    permission_classes = [IsManager]

    def put(self, request, price_id):
        try:
            price = MenuItemPrice.objects.get(pk=price_id)
        except MenuItemPrice.DoesNotExist:
            raise Http404("Menu item size not found.")
        ser = recipes.RecipeInput(data=request.data)
        ser.is_valid(raise_exception=True)
        recipes.set_recipe(price, ser.validated_data["lines"])
        return Response(recipes.overview())


class DealContentsView(APIView):
    """PUT replaces which menu items a deal contains."""
    permission_classes = [IsManager]

    def put(self, request, deal_id):
        try:
            deal = Deal.objects.get(pk=deal_id)
        except Deal.DoesNotExist:
            raise Http404("Deal not found.")
        ser = recipes.DealContentsInput(data=request.data)
        ser.is_valid(raise_exception=True)
        recipes.set_deal_contents(deal, ser.validated_data["components"])
        return Response(recipes.overview())


class AdjustmentView(APIView):
    """Waste, or a correction. POST only: nothing here edits an old row, it adds a new one."""
    permission_classes = [IsManager]

    def post(self, request):
        ser = AdjustmentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            mv, created = services.post_adjustment(request.user, ser.validated_data)
        except IntegrityError:    # the same client_ref arrived twice at once; the other one won
            mv, created = services.StockMovement.objects.get(client_ref=ser.validated_data["client_ref"]), False
        return Response({"id": mv.id, "material": mv.material_id, "quantity": str(mv.quantity), "type": mv.movement_type},
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class StockCountView(APIView):
    permission_classes = [IsManager]

    def post(self, request):
        ser = CountCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            count, created = services.post_count(request.user, ser.validated_data)
        except IntegrityError:
            count, created = StockCount.objects.get(client_ref=ser.validated_data["client_ref"]), False
        return Response(count_detail(count), status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class AlertsView(APIView):
    """Feeds the low-stock badge on the Inventory card."""
    permission_classes = [IsManager]

    def get(self, request):
        return Response({"low_count": reports.stock_summary()["low_count"]})
