"""
Sign-in tokens for website customers.

Deliberately separate from the staff (POS) tokens:
  * signed with a DIFFERENT key, so a customer token can never be accepted as a
    staff token (or the other way round);
  * carry a fingerprint of the password, so changing the password - or staff
    removing the account - instantly invalidates every token issued before.
"""
import hashlib
import time

import jwt
from django.conf import settings

from .models import Customer

ALGORITHM = "HS256"
ISSUER = "woknbun-customers"


def _key():
    return hashlib.sha256(f"customer-tokens:{settings.SECRET_KEY}".encode()).hexdigest()


def _password_fingerprint(customer):
    return hashlib.sha256((customer.password or "").encode()).hexdigest()[:16]


def _make(customer, kind, seconds):
    now = int(time.time())
    return jwt.encode(
        {"iss": ISSUER, "sub": str(customer.pk), "typ": kind, "iat": now, "exp": now + seconds, "pwv": _password_fingerprint(customer)},
        _key(), algorithm=ALGORITHM)


def issue_tokens(customer):
    access = int(getattr(settings, "CUSTOMER_ACCESS_MINUTES", 30) * 60)
    refresh = int(getattr(settings, "CUSTOMER_REFRESH_DAYS", 30) * 86400)
    return {"access": _make(customer, "access", access), "refresh": _make(customer, "refresh", refresh)}


def customer_from_token(token, kind):
    """The customer this token belongs to, or None if it is forged, expired, the wrong kind, or out of date."""
    try:
        data = jwt.decode(token, _key(), algorithms=[ALGORITHM], issuer=ISSUER,
                          options={"require": ["exp", "iat", "sub", "typ", "iss"]})
    except jwt.PyJWTError:
        return None
    if data.get("typ") != kind:
        return None
    customer = Customer.objects.filter(pk=data["sub"]).first()
    if customer is None or not customer.has_account or data.get("pwv") != _password_fingerprint(customer):
        return None
    return customer