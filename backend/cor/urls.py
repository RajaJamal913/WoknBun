from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CancellationReportView, CategoryViewSet, ConfigView, DealViewSet, HourlySalesView, MenuItemViewSet,
    OrderViewSet, PosCancelOrderView, PosOrderListCreateView, PosRefundOrderView, PosSettleOrderView,
    SalesReportView, SalesSummaryView,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="cor-category")
router.register("menu-items", MenuItemViewSet, basename="cor-menu-item")
router.register("deals", DealViewSet, basename="cor-deal")
router.register("orders", OrderViewSet, basename="cor-order")

urlpatterns = [
    path("config/", ConfigView.as_view(), name="cor-config"),
    # POS terminal: order history, record a sale, settle / refund / cancel
    path("pos-orders/", PosOrderListCreateView.as_view(), name="cor-pos-orders"),
    path("pos-orders/<int:order_id>/settle/", PosSettleOrderView.as_view(), name="cor-pos-order-settle"),
    path("pos-orders/<int:order_id>/refund/", PosRefundOrderView.as_view(), name="cor-pos-order-refund"),
    path("pos-orders/<int:order_id>/cancel/", PosCancelOrderView.as_view(), name="cor-pos-order-cancel"),
    # Reports for this restaurant only
    path("reports/sales-summary/", SalesSummaryView.as_view(), name="cor-report-summary"),
    path("reports/sales/", SalesReportView.as_view(), name="cor-report-sales"),
    path("reports/hourly/", HourlySalesView.as_view(), name="cor-report-hourly"),
    path("reports/cancellations/", CancellationReportView.as_view(), name="cor-report-cancellations"),
] + router.urls
