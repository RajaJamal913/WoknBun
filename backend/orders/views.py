from django.conf import settings
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import Order
from .serializers import OrderSerializer


class OrderCreateView(generics.CreateAPIView):
    """Public: customers place cash-on-delivery orders without an account."""
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "order_create"


class ConfigView(APIView):
    """Business constants for clients to DISPLAY. The server still computes every total."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({
            "tax_rate": str(settings.TAX_RATE),
            "delivery_charges": str(settings.DELIVERY_CHARGES),
        })
