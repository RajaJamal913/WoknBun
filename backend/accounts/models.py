import uuid

from django.db import models


def generate_auth_token():
    """Not used any more (the sign-in token was removed). Kept ONLY because the old migration
    0001_initial refers to it by name - deleting it would break `manage.py migrate`."""
    return uuid.uuid4().hex


class Customer(models.Model):
    """
    A person who orders from us - created automatically from the phone number on
    their first website or counter order. There is no website login: the phone
    number is only used to recognise them and to show their history to staff.
    """
    GENDER_CHOICES = [
        ("", "Prefer not to say"),
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    ]

    full_name = models.CharField(max_length=150)
    # Canonical form, e.g. +923113925176 (see accounts/phone.py). Unique, so one
    # person = one record however they type their number.
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    alt_phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)  # staff notes, e.g. "allergic to nuts"
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    # ---- optional website login -------------------------------------------
    # Empty = a guest (ordered without an account). Otherwise a HASHED password
    # (never the real one). The phone number is the sign-in name.
    password = models.CharField(max_length=128, blank=True)
    account_created_at = models.DateTimeField(null=True, blank=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    # A signed-in customer shows up as `request.user` on the customer endpoints.
    # They are NOT Django users: these flags make absolutely sure that, if one
    # ever reached a staff check, it would be treated as an ordinary outsider.
    is_superuser = False
    is_staff = False
    is_active = True
    is_anonymous = False
    is_authenticated = True

    class Meta:
        ordering = ["-created_at"]

    @property
    def has_account(self):
        return bool(self.password)

    def __str__(self):
        return f"{self.full_name} ({self.phone or 'no phone'})"