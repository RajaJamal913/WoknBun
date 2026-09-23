import uuid
from django.db import models


def generate_auth_token():
    return uuid.uuid4().hex


class Customer(models.Model):
    GENDER_CHOICES = [
        ("", "Prefer not to say"),
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    ]

    full_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    mobile_number = models.CharField(max_length=20)

    # Simple opaque token returned on register/login so the frontend can
    # recognise this customer on future visits. Not a full auth system
    # (no password, no expiry) - fine for a lightweight "remember me by
    # email" flow, but swap for real session/JWT auth before handling
    # anything sensitive.
    auth_token = models.CharField(
        max_length=64, unique=True, default=generate_auth_token, editable=False
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} <{self.email}>"