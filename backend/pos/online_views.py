from datetime import timedelta

from django.db.models import Count, Max
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order as OnlineOrder
from . import online
from .online_serializers import OnlineOrderSerializer
from .permissions import IsCashierOrAbove
from .serializers import OrderSerializer as PosOrderSerializer

DONE_WINDOW = timedelta(days=3)
DONE_LIMIT = 100
IN_PROGRESS = ["confirmed", "preparing", "out_for_delivery"]


def _base():
    return OnlineOrder.objects.select_related("accepted_by", "pos_order").prefetch_related("items")


class OnlineOrderListView(APIView):
    """?group=new (waiting for a decision) | active (being worked) | done (last 3 days)."""
    permission_classes = [IsCashierOrAbove]

    def get(self, request):
        group = request.query_params.get("group", "new")
        if group == "active":
            qs = _base().filter(status__in=IN_PROGRESS).order_by("created_at")          # oldest first
        elif group == "done":
            since = timezone.now() - DONE_WINDOW
            qs = (_base().filter(status__in=["delivered", "cancelled"])
                  .annotate(changed=Coalesce("status_changed_at", "created_at")).filter(changed__gte=since)
                  .order_by("-changed")[:DONE_LIMIT])                                   # newest first
        else:
            qs = _base().filter(status="pending").order_by("created_at")                # oldest first
        return Response(OnlineOrderSerializer(qs, many=True).data)


class OnlineOrderSummaryView(APIView):
    """Cheap counts the terminal polls to show the badge and announce new orders."""
    permission_classes = [IsCashierOrAbove]

    def get(self, request):
        counts = dict(OnlineOrder.objects.filter(status__in=["pending"] + IN_PROGRESS)
                      .values_list("status").annotate(n=Count("id")))
        newest = OnlineOrder.objects.filter(status="pending").aggregate(m=Max("id"))["m"]
        return Response({
            "new": counts.get("pending", 0),
            "active": sum(counts.get(s, 0) for s in IN_PROGRESS),
            "latest_new_id": newest,
        })


class OnlineOrderActionView(APIView):
    permission_classes = [IsCashierOrAbove]

    def post(self, request, order_id, action):
        try:
            order, sale = online.apply_action(order_id, action, request.user, request.data.get("reason", ""))
        except online.OnlineOrderError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        order = _base().get(pk=order.pk)
        return Response({
            "order": OnlineOrderSerializer(order).data,
            "pos_order": PosOrderSerializer(sale).data if sale else None,
        })