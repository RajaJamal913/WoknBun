from rest_framework import authentication, exceptions

from . import tokens


class CustomerAuthentication(authentication.BaseAuthentication):
    """`Authorization: Bearer <customer access token>`. A bad token is a 401. Used ONLY on the customer endpoints."""

    def authenticate(self, request):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return None
        customer = tokens.customer_from_token(header[7:].strip(), "access")
        if customer is None:
            raise exceptions.AuthenticationFailed("Please sign in again.")
        return (customer, None)

    def authenticate_header(self, request):
        return "Bearer"


class OptionalCustomerAuthentication(CustomerAuthentication):
    """For checkout: a missing, expired or bad token simply means 'guest' - the order must still go through."""

    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except exceptions.AuthenticationFailed:
            return None