from rest_framework.test import APITestCase

from menu.testing import reset_throttles
from .models import Customer


class CustomerAuthTests(APITestCase):
    def setUp(self):
        reset_throttles()

    def test_register_and_login_never_expose_auth_token(self):
        res = self.client.post("/api/auth/register/", {
            "full_name": "Sara", "email": "s@example.com", "mobile_number": "0300"}, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertNotIn("auth_token", res.data)

        res = self.client.post("/api/auth/login/", {"email": "S@EXAMPLE.com"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("auth_token", res.data)
        self.assertEqual(Customer.objects.count(), 1)
