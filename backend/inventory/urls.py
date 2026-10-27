from django.urls import path

from . import views

urlpatterns = [
    path("inventory/materials/", views.MaterialListCreateView.as_view(), name="inv-materials"),
    path("inventory/materials/<int:pk>/", views.MaterialDetailView.as_view(), name="inv-material"),
    path("inventory/suppliers/", views.SupplierListCreateView.as_view(), name="inv-suppliers"),
    path("inventory/suppliers/<int:pk>/", views.SupplierDetailView.as_view(), name="inv-supplier"),
    path("inventory/purchase-invoices/", views.PurchaseInvoiceListCreateView.as_view(), name="inv-purchases"),
    path("inventory/purchase-invoices/<int:invoice_id>/", views.PurchaseInvoiceDetailView.as_view(), name="inv-purchase"),
    path("inventory/purchase-invoices/<int:invoice_id>/void/", views.PurchaseInvoiceVoidView.as_view(), name="inv-purchase-void"),
    path("inventory/purchase-invoices/<int:invoice_id>/payments/", views.PurchasePaymentView.as_view(), name="inv-purchase-pay"),
    path("inventory/recipes/", views.RecipeOverviewView.as_view(), name="inv-recipes"),
    path("inventory/recipes/<int:price_id>/", views.RecipeDetailView.as_view(), name="inv-recipe"),
    path("inventory/deals/<int:deal_id>/contents/", views.DealContentsView.as_view(), name="inv-deal-contents"),
    path("inventory/adjustments/", views.AdjustmentView.as_view(), name="inv-adjustments"),
    path("inventory/stock-counts/", views.StockCountView.as_view(), name="inv-stock-counts"),
    path("inventory/alerts/", views.AlertsView.as_view(), name="inv-alerts"),
    path("inventory/reports/stock-summary/", views.StockSummaryView.as_view(), name="inv-report-summary"),
    path("inventory/reports/stock-ledger/", views.StockLedgerView.as_view(), name="inv-report-ledger"),
    path("inventory/reports/purchases/", views.PurchaseReportView.as_view(), name="inv-report-purchases"),
]
