from django.db import IntegrityError
from django.http import Http404
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Customer
from accounts.phone import normalize_phone
from accounts.services import find_or_create_customer
from . import customers
from .permissions import IsCashierOrAbove, IsManager


class CustomerWriteSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=30)
    email = serializers.EmailField(required=False, allow_blank=True)
    alt_phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)

    def validate_full_name(self, v):
        v = v.strip()
        if not v:
            raise serializers.ValidationError("Enter the customer's name.")
        return v

    def validate_phone(self, v):
        phone = normalize_phone(v)
        if not phone:
            raise serializers.ValidationError("Enter a valid mobile number, e.g. 0300 1234567.")
        return phone


class CustomerListCreateView(APIView):
    permission_classes = [IsCashierOrAbove]

    def get(self, request):
        rows = [customers.summary(c) for c in customers.search(request.query_params.get("q", ""))]
        return Response(rows)

    def post(self, request):
        """Quick-add at the till. If that phone is already a customer, hand back that customer (no duplicate)."""
        ser = CustomerWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        before = Customer.objects.filter(phone=d["phone"]).exists()
        c = find_or_create_customer(d["full_name"], d["phone"], d.get("email", ""), d.get("alt_phone", ""))
        if d.get("notes") and not c.notes:
            c.notes = d["notes"]; c.save(update_fields=["notes"])
        body = customers.detail(c.id)
        body["created"] = not before
        return Response(body, status=status.HTTP_200_OK if before else status.HTTP_201_CREATED)


class CustomerDetailView(APIView):
    permission_classes = [IsCashierOrAbove]

    def get(self, request, customer_id):
        body = customers.detail(customer_id)
        if body is None:
            raise Http404("Customer not found.")
        return Response(body)

    def patch(self, request, customer_id):
        try:
            c = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            raise Http404("Customer not found.")
        ser = CustomerWriteSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        if "phone" in d and Customer.objects.filter(phone=d["phone"]).exclude(pk=c.pk).exists():
            return Response({"phone": ["Another customer already has this number."]}, status=status.HTTP_400_BAD_REQUEST)
        for field in ("full_name", "phone", "email", "alt_phone", "notes"):
            if field in d:
                setattr(c, field, d[field])
        try:
            c.save()
        except IntegrityError:  # someone saved the same number a moment ago
            return Response({"phone": ["Another customer already has this number."]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(customers.detail(c.id))


class CustomerAccountView(APIView):
    """Remove a customer's WEBSITE LOGIN (not the customer): the way a forgotten password is handled.
    Their orders and history stay. Every sign-in token they hold stops working at once, and they can
    simply register again. Managers only - confirm who you're talking to first."""
    permission_classes = [IsManager]

    def delete(self, request, customer_id):
        try:
            c = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            raise Http404("Customer not found.")
        c.password = ""
        c.account_created_at = None
        c.last_login_at = None
        c.save(update_fields=["password", "account_created_at", "last_login_at"])
        return Response(customers.detail(c.id))