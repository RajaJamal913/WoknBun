from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    OpenShiftView, CloseShiftView, CurrentShiftView,
    OrderListCreateView, SettleOrderView, RefundOrderView, CancelOrderView,
)
from .report_views import (
    MeView, DashboardView, SalesSummaryView, SalesReportView, HourlySalesView, CancellationReportView,
)

urlpatterns = [
    path("pos/auth/login/", TokenObtainPairView.as_view(), name="pos-login"),
    path("pos/auth/refresh/", TokenRefreshView.as_view(), name="pos-refresh"),
    path("pos/shifts/open/", OpenShiftView.as_view(), name="pos-shift-open"),
    path("pos/shifts/current/", CurrentShiftView.as_view(), name="pos-shift-current"),
    path("pos/shifts/<int:shift_id>/close/", CloseShiftView.as_view(), name="pos-shift-close"),
    path("pos/orders/", OrderListCreateView.as_view(), name="pos-orders"),
    path("pos/orders/<int:order_id>/settle/", SettleOrderView.as_view(), name="pos-order-settle"),
    path("pos/orders/<int:order_id>/refund/", RefundOrderView.as_view(), name="pos-order-refund"),
    path("pos/orders/<int:order_id>/cancel/", CancelOrderView.as_view(), name="pos-order-cancel"),
    path("pos/me/", MeView.as_view(), name="pos-me"),
    path("pos/dashboard/", DashboardView.as_view(), name="pos-dashboard"),
    path("pos/reports/sales-summary/", SalesSummaryView.as_view(), name="pos-report-summary"),
    path("pos/reports/sales/", SalesReportView.as_view(), name="pos-report-sales"),
    path("pos/reports/hourly/", HourlySalesView.as_view(), name="pos-report-hourly"),
    path("pos/reports/cancellations/", CancellationReportView.as_view(), name="pos-report-cancellations"),
]