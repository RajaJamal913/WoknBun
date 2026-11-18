from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CancellationReportView, CategoryViewSet, ConfigView, DealViewSet, HourlySalesView, MenuItemViewSet,
    OrderViewSet, PosCancelOrderView, PosOrderListCreateView, PosRefundOrderView, PosSettleOrderView,
    SalesReportView, SalesSummaryView,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="shangyaki-category")
router.register("menu-items", MenuItemViewSet, basename="shangyaki-menu-item")
router.register("deals", DealViewSet, basename="shangyaki-deal")
router.register("orders", OrderViewSet, basename="shangyaki-order")

urlpatterns = [
    path("config/", ConfigView.as_view(), name="shangyaki-config"),
    # POS terminal: order history, record a sale, settle / refund / cancel
    path("pos-orders/", PosOrderListCreateView.as_view(), name="shangyaki-pos-orders"),
    path("pos-orders/<int:order_id>/settle/", PosSettleOrderView.as_view(), name="shangyaki-pos-order-settle"),
    path("pos-orders/<int:order_id>/refund/", PosRefundOrderView.as_view(), name="shangyaki-pos-order-refund"),
    path("pos-orders/<int:order_id>/cancel/", PosCancelOrderView.as_view(), name="shangyaki-pos-order-cancel"),
    # Reports for this restaurant only
    path("reports/sales-summary/", SalesSummaryView.as_view(), name="shangyaki-report-summary"),
    path("reports/sales/", SalesReportView.as_view(), name="shangyaki-report-sales"),
    path("reports/hourly/", HourlySalesView.as_view(), name="shangyaki-report-hourly"),
    path("reports/cancellations/", CancellationReportView.as_view(), name="shangyaki-report-cancellations"),
] + router.urls
