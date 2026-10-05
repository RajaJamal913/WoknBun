from decimal import Decimal

from rest_framework.test import APITestCase

from menu.testing import make_menu, reset_throttles
from .models import Order


class OnlineOrderTests(APITestCase):
    def setUp(self):
        reset_throttles()
        self.m = make_menu()
        self.url = "/api/orders/"

    def payload(self, items):
        return {
            "full_name": "Ali", "mobile_number": "0300", "address_line": "House 1",
            "payment_method": "cod", "items": items,
        }

    def test_totals_come_from_server_prices(self):
        # 2 x Large pizza (1999) + 1 Fries (399) = 4397 ; tax 16% = 703.52 ; + 250 delivery
        res = self.client.post(self.url, self.payload([
            {"price_id": self.m["large"].id, "quantity": 2},
            {"price_id": self.m["fries"].id, "quantity": 1},
        ]), format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(Decimal(res.data["subtotal"]), Decimal("4397.00"))
        self.assertEqual(Decimal(res.data["tax_amount"]), Decimal("703.52"))
        self.assertEqual(Decimal(res.data["grand_total"]), Decimal("5350.52"))

    def test_client_cannot_set_its_own_price(self):
        res = self.client.post(self.url, self.payload([
            {"price_id": self.m["large"].id, "quantity": 1, "unit_price": "1", "line_total": "1"},
        ]), format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Decimal(res.data["items"][0]["unit_price"]), Decimal("1999.00"))
        self.assertEqual(Order.objects.get().items.get().menu_item_id, self.m["pizza"].id)

    def test_deal_line_priced_by_server(self):
        res = self.client.post(self.url, self.payload([{"deal_id": self.m["deal"].id, "quantity": 2}]), format="json")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(Decimal(res.data["subtotal"]), Decimal("1998.00"))
        self.assertEqual(res.data["items"][0]["size_label"], "Deal")

    def test_rejects_bad_lines(self):
        bad = [
            [],  # empty cart
            [{"quantity": 1}],  # neither id
            [{"price_id": self.m["fries"].id, "deal_id": self.m["deal"].id, "quantity": 1}],  # both
            [{"price_id": self.m["fries"].id, "quantity": 0}],  # zero qty
            [{"price_id": self.m["fries"].id, "quantity": -3}],
            [{"price_id": self.m["fries"].id, "quantity": 100}],
            [{"price_id": self.m["hidden"].id, "quantity": 1}],  # inactive item
            [{"price_id": 999999, "quantity": 1}],  # unknown
        ]
        for items in bad:
            res = self.client.post(self.url, self.payload(items), format="json")
            self.assertEqual(res.status_code, 400, items)
        self.assertEqual(Order.objects.count(), 0)

    def test_config_endpoint_is_public(self):
        res = self.client.get("/api/config/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["tax_rate"], "0.16")
        self.assertEqual(res.data["delivery_charges"], "250.00")

    def test_order_creation_is_throttled(self):
        from django.conf import settings
        from rest_framework.throttling import ScopedRateThrottle
        ScopedRateThrottle.THROTTLE_RATES = {**settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"], "order_create": "2/min"}
        try:
            body = self.payload([{"price_id": self.m["fries"].id, "quantity": 1}])
            codes = [self.client.post(self.url, body, format="json").status_code for _ in range(3)]
        finally:
            ScopedRateThrottle.THROTTLE_RATES = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
        self.assertEqual(codes, [201, 201, 429])
