from rest_framework import serializers
from .models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "id", "full_name", "email", "gender",
            "date_of_birth", "mobile_number", "created_at",
        ]
        # auth_token is deliberately NOT exposed: email-only sign-in must not
        # hand a credential to whoever types an address.
        read_only_fields = ["id", "created_at"]


class RegisterSerializer(serializers.ModelSerializer):
    # Override the field so DRF's automatic UniqueValidator (which fires
    # before validate_email() and produces a generic message) doesn't
    # short-circuit our friendlier duplicate-email message below.
    email = serializers.EmailField(validators=[])

    class Meta:
        model = Customer
        fields = ["full_name", "email", "gender", "date_of_birth", "mobile_number"]

    def validate_email(self, value):
        if Customer.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "An account with this email already exists. Please sign in instead."
            )
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()