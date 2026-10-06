from datetime import timedelta

from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from . import reports
from .permissions import (
    CanViewDashboard, CanViewReports, IsPOSStaff, can_discount, can_take_orders, can_view_dashboard,
    can_view_reports, staff_role,
)

MAX_RANGE_DAYS = 366


def _date_param(request, name, default):
    raw = request.query_params.get(name)
    if not raw:
        return default
    value = parse_date(raw)
    if value is None:
        raise ValidationError({name: "Use the format YYYY-MM-DD."})
    return value


def _range(request):
    today = timezone.localdate()
    date_from = _date_param(request, "from", today)
    date_to = _date_param(request, "to", date_from)
    if date_to < date_from:
        raise ValidationError({"to": "'to' cannot be before 'from'."})
    if (date_to - date_from) > timedelta(days=MAX_RANGE_DAYS):
        raise ValidationError({"to": f"Choose a range of at most {MAX_RANGE_DAYS} days."})
    return date_from, date_to


class MeView(APIView):
    """Who is signed in and what role - the terminal uses this to show manager screens."""
    permission_classes = [IsPOSStaff]

    def get(self, request):
        u = request.user
        return Response({
            "username": u.get_username(),
            "name": u.get_full_name() or u.get_username(),
            "role": staff_role(u),
            # The terminal shows only the screens/buttons this account may use.
            "can_view_dashboard": can_view_dashboard(u),
            "can_view_reports": can_view_reports(u),
            "can_take_orders": can_take_orders(u),
            "can_discount": can_discount(u),
        })


class DashboardView(APIView):
    permission_classes = [CanViewDashboard]

    def get(self, request):
        return Response(reports.dashboard(_date_param(request, "date", timezone.localdate())))


class SalesSummaryView(APIView):
    permission_classes = [CanViewReports]

    def get(self, request):
        return Response(reports.sales_summary(*_range(request)))


class SalesReportView(APIView):
    permission_classes = [CanViewReports]

    def get(self, request):
        return Response(reports.item_sales(*_range(request)))


class HourlySalesView(APIView):
    permission_classes = [CanViewReports]

    def get(self, request):
        return Response(reports.hourly_sales(_date_param(request, "date", timezone.localdate())))


class CancellationReportView(APIView):
    permission_classes = [CanViewReports]

    def get(self, request):
        return Response(reports.cancellations(*_range(request)))