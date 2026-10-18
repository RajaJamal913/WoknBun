from rest_framework.test import APITestCase

from menu.testing import reset_throttles
from .models import Customer

PASSWORD = "Sup3r-secret-pw"


class CustomerAuthTests(APITestCase):
    def setUp(self):
        reset_throttles()

    def test_register_and_login_never_expose_auth_token(self):
        res = self.client.post("/api/auth/register/", {
            "full_name": "Sara", "email": "s@example.com", "phone": "0300 1234567", "password": PASSWORD}, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertNotIn("auth_token", res.data)
        self.assertIn("access", res.data["tokens"])
        self.assertEqual(res.data["customer"]["phone"], "+923001234567")

        # sign in with the phone number, typed differently, and with the email
        for identifier in ("03001234567", "S@EXAMPLE.com"):
            res = self.client.post("/api/auth/login/", {"identifier": identifier, "password": PASSWORD}, format="json")
            self.assertEqual(res.status_code, 200, res.content)
            self.assertNotIn("auth_token", res.data)
        self.assertEqual(Customer.objects.count(), 1)

    def test_wrong_password_is_rejected_with_a_generic_message(self):
        self.client.post("/api/auth/register/", {
            "full_name": "Sara", "phone": "03001234567", "password": PASSWORD}, format="json")
        res = self.client.post("/api/auth/login/", {"identifier": "03001234567", "password": "nope-nope-nope"}, format="json")
        self.assertEqual(res.status_code, 400)
