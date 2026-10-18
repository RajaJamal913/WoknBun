"""
Website customer accounts: register, sign in, profile, change password, my orders.
Customers are identified by their phone number (see services.py). Passwords are
hashed by Django; sign-in is rate limited and locks out after repeated failures.
"""
import hashlib
from functools import lru_cache

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from orders.models import Order as WebOrder
from . import tokens
from .authentication import CustomerAuthentication
from .models import Customer
from .phone import normalize_phone

MAX_FAILED_LOGINS = 10
LOCKOUT_SECONDS = 15 * 60
WRONG_LOGIN = "Wrong mobile number, email or password."


class IsCustomer(permissions.BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.user, Customer)


def profile(c):
    return {"id": c.id, "full_name": c.full_name, "phone": c.phone, "email": c.email,
            "gender": c.gender, "date_of_birth": c.date_of_birth.isoformat() if c.date_of_birth else None}


def session_body(c):
    return {"tokens": tokens.issue_tokens(c), "customer": profile(c)}


class _Password(serializers.CharField):
    """Runs Django's password rules (length, not too common, not all digits...)."""
    def __init__(self, **kw):
        super().__init__(write_only=True, max_length=128, trim_whitespace=False, **kw)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value


class RegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=30)
    email = serializers.EmailField(required=False, allow_blank=True)
    gender = serializers.ChoiceField(choices=["male", "female", "other"], required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    password = _Password()

    def validate_full_name(self, v):
        v = v.strip()
        if not v:
            raise serializers.ValidationError("Enter your name.")
        return v

    def validate_phone(self, v):
        phone = normalize_phone(v)
        if not phone:
            raise serializers.ValidationError("Enter a valid mobile number, e.g. 0300 1234567.")
        return phone


class AuthThrottle(ScopedRateThrottle):
    scope = "customer_auth"


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthThrottle]
    throttle_scope = "customer_auth"

    def post(self, request):
        ser = RegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        taken = {"phone": ["This number already has an account. Please sign in."]}
        try:
            with transaction.atomic():
                c = Customer.objects.select_for_update().filter(phone=d["phone"]).first()
                if c is not None and c.has_account:
                    return Response(taken, status=status.HTTP_400_BAD_REQUEST)
                if c is None:
                    c = Customer(phone=d["phone"])
                # An existing record here is a GUEST who has ordered before: they claim it. Their name and
                # email are replaced by what they just typed (the phone is not verified yet, so nothing
                # stored about the previous guest is ever shown back to the new account holder).
                c.full_name = d["full_name"]
                c.email = d.get("email", "")
                if d.get("gender"):
                    c.gender = d["gender"]
                if d.get("date_of_birth"):
                    c.date_of_birth = d["date_of_birth"]
                c.password = make_password(d["password"])
                c.account_created_at = c.last_login_at = timezone.now()
                c.save()
        except IntegrityError:  # two people registered the same new number at once
            return Response(taken, status=status.HTTP_400_BAD_REQUEST)
        return Response(session_body(c), status=status.HTTP_201_CREATED)


@lru_cache(maxsize=1)
def _dummy_hash():
    return make_password("not-a-real-password")


def _find_account(identifier):
    ident = identifier.strip()
    if "@" in ident:
        matches = list(Customer.objects.filter(email__iexact=ident).exclude(password="")[:2])
        return matches[0] if len(matches) == 1 else None   # an email shared by two accounts can't identify one
    phone = normalize_phone(ident)
    return Customer.objects.filter(phone=phone).exclude(password="").first() if phone else None


def _fail_key(identifier):
    ident = identifier.strip().lower()
    ident = normalize_phone(ident) or ident
    return "customer-login-fails:" + hashlib.sha256(ident.encode()).hexdigest()


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthThrottle]
    throttle_scope = "customer_auth"

    def post(self, request):
        identifier = str(request.data.get("identifier", ""))
        password = str(request.data.get("password", ""))
        if not identifier.strip() or not password:
            return Response({"detail": "Enter your mobile number (or email) and password."}, status=status.HTTP_400_BAD_REQUEST)

        key = _fail_key(identifier)
        if cache.get(key, 0) >= MAX_FAILED_LOGINS:
            return Response({"detail": "Too many wrong attempts. Please try again in 15 minutes."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        customer = _find_account(identifier)
        # Always do one password check - same work whether or not the account exists - and always give the
        # same message, so the answer never reveals which numbers or emails have accounts.
        ok = check_password(password, customer.password if customer else _dummy_hash())
        if not (customer and ok):
            cache.set(key, cache.get(key, 0) + 1, LOCKOUT_SECONDS)
            return Response({"detail": WRONG_LOGIN}, status=status.HTTP_400_BAD_REQUEST)

        cache.delete(key)
        customer.last_login_at = timezone.now()
        customer.save(update_fields=["last_login_at"])
        return Response(session_body(customer))


class RefreshView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthThrottle]
    throttle_scope = "customer_auth"

    def post(self, request):
        customer = tokens.customer_from_token(str(request.data.get("refresh", "")), "refresh")
        if customer is None:
            return Response({"detail": "Please sign in again."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(tokens.issue_tokens(customer))


class ProfileUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150, required=False)
    email = serializers.EmailField(required=False, allow_blank=True)
    gender = serializers.ChoiceField(choices=["male", "female", "other"], required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)

    def validate_full_name(self, v):
        v = v.strip()
        if not v:
            raise serializers.ValidationError("Enter your name.")
        return v


class MeView(APIView):
    authentication_classes = [CustomerAuthentication]
    permission_classes = [IsCustomer]

    def get(self, request):
        return Response(profile(request.user))

    def patch(self, request):
        ser = ProfileUpdateSerializer(data=request.data)   # the phone number can't be changed here: it is the sign-in name
        ser.is_valid(raise_exception=True)
        c = request.user
        for field, value in ser.validated_data.items():
            setattr(c, field, value)
        c.save()
        return Response(profile(c))


class ChangePasswordView(APIView):
    authentication_classes = [CustomerAuthentication]
    permission_classes = [IsCustomer]
    throttle_classes = [AuthThrottle]
    throttle_scope = "customer_auth"

    def post(self, request):
        c = request.user
        if not check_password(str(request.data.get("current_password", "")), c.password):
            return Response({"current_password": ["Your current password is wrong."]}, status=status.HTTP_400_BAD_REQUEST)
        ser = serializers.Serializer(data=request.data)
        new = _Password()
        try:
            value = new.run_validation(request.data.get("new_password", None))
        except serializers.ValidationError as e:
            return Response({"new_password": e.detail}, status=status.HTTP_400_BAD_REQUEST)
        c.password = make_password(value)
        c.save(update_fields=["password"])
        return Response(session_body(c))   # every older token stops working; here are fresh ones


class MyOrdersView(APIView):
    """Orders placed while signed in. Orders someone placed as a guest with the same number are NOT shown:
    the phone isn't verified, so a number alone must never unlock somebody's order history."""
    authentication_classes = [CustomerAuthentication]
    permission_classes = [IsCustomer]

    def get(self, request):
        orders = (WebOrder.objects.filter(customer=request.user, placed_by_account=True)
                  .prefetch_related("items").order_by("-created_at")[:50])
        return Response([{
            "id": o.id, "created_at": o.created_at.isoformat(), "status": o.status, "cancel_reason": o.cancel_reason,
            "address_line": o.address_line, "subtotal": str(o.subtotal), "delivery_charges": str(o.delivery_charges),
            "tax_amount": str(o.tax_amount), "grand_total": str(o.grand_total),
            "items": [{"item_name": i.item_name, "size_label": i.size_label, "quantity": i.quantity, "line_total": str(i.line_total)} for i in o.items.all()],
        } for o in orders])