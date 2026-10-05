import uuid
from datetime import timedelta
from decimal import Decimal

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Order, Shift
from .tests import POSBase, client_for


class ReportTests(POSBase):
    """
    Today:  A 2x Large pizza (3998 + 639.68 tax = 4637.68, cash)
            B 1x Fries       (399  + 63.84       = 462.84,  card)
            C 1x Small pizza (649  + 103.84      = 752.84,  card, then REFUNDED)
            D 1x Fries cancelled before payment (462.84)
            E 1x Fries still open
    Yesterday: F 1x Large (1999 + 319.84 = 2318.84, cash)
    """

    def setUp(self):
        super().setUp()
        m = self.m
        self.A = self._settle(self._punch(m["large"], 2), "cash")
        self.B = self._settle(self._punch(m["fries"], 1), "card")
        self.C = self._settle(self._punch(m["small"], 1), "card")
        res = client_for(self.mgr).post(f"/api/pos/orders/{self.C}/refund/", {"reason": "cold food"}, format="json")
        assert res.status_code == 200, res.content
        self.D = self._punch(m["fries"], 1)
        assert client_for(self.alice).post(f"/api/pos/orders/{self.D}/cancel/").status_code == 200
        self.E = self._punch(m["fries"], 1)

        self.F = self._settle(self._punch(m["large"], 1), "cash")
        yesterday = timezone.now() - timedelta(days=1)
        Order.objects.filter(id=self.F).update(settled_at=yesterday, created_at=yesterday)

    def _punch(self, price, qty):
        res, _ = self.punch(items=[{"price_id": price.id, "quantity": qty}])
        assert res.status_code == 201, res.content
        return res.data["id"]

    def _settle(self, oid, method):
        body = {"payment_method": method, "amount_tendered": "100000"}
        assert client_for(self.alice).post(f"/api/pos/orders/{oid}/settle/", body, format="json").status_code == 200
        return oid

    def get(self, path, user=None, **params):
        return client_for(user or self.mgr).get(f"/api/pos/{path}", params)

    # ---- access ----
    REPORTS = ("reports/sales-summary/", "reports/sales/", "reports/hourly/", "reports/cancellations/")

    def test_every_staff_role_can_see_the_dashboard(self):
        for user in (self.alice, self.kitchen, self.mgr):
            self.assertEqual(self.get("dashboard/", user=user).status_code, 200, user.username)
        self.assertEqual(self.get("dashboard/", user=self.nobody).status_code, 403, "non-staff still blocked")
        self.assertEqual(APIClient().get("/api/pos/dashboard/").status_code, 401)

    def test_detailed_reports_are_managers_only_by_default(self):
        for path in self.REPORTS:
            self.assertEqual(self.get(path, user=self.alice).status_code, 403, path)
            self.assertEqual(self.get(path, user=self.kitchen).status_code, 403, path)
            self.assertEqual(self.get(path).status_code, 200, path)

    def test_reports_can_be_opened_to_everyone_via_settings(self):
        with override_settings(POS_REPORT_ROLES=("cashier", "kitchen", "manager", "admin")):
            for path in self.REPORTS:
                self.assertEqual(self.get(path, user=self.alice).status_code, 200, path)
                self.assertEqual(self.get(path, user=self.kitchen).status_code, 200, path)
            self.assertEqual(self.get(self.REPORTS[0], user=self.nobody).status_code, 403)

    def test_me_reports_role_and_capabilities(self):
        caps = lambda u: {k: v for k, v in self.get("me/", user=u).data.items() if k.startswith("can_")}
        self.assertEqual(self.get("me/", user=self.alice).data["role"], "cashier")
        self.assertEqual(caps(self.alice), {"can_view_dashboard": True, "can_view_reports": False, "can_take_orders": True})
        self.assertEqual(caps(self.kitchen), {"can_view_dashboard": True, "can_view_reports": False, "can_take_orders": False})
        self.assertEqual(caps(self.mgr), {"can_view_dashboard": True, "can_view_reports": True, "can_take_orders": True})
        self.assertEqual(self.get("me/", user=self.nobody).status_code, 403)

    # ---- sales summary ----
    def test_sales_summary_today(self):
        d = self.get("reports/sales-summary/").data
        self.assertEqual(d["orders"], 3)  # A, B, C (settled at some point today)
        self.assertEqual(d["items_total"], "5046.00")
        self.assertEqual(d["tax"], "807.36")
        self.assertEqual(d["total_sales"], "5853.36")
        self.assertEqual((d["refunds_count"], d["refunds_total"]), (1, "752.84"))
        self.assertEqual(d["net_sales"], "5100.52")
        self.assertEqual(d["avg_order_value"], "2550.26")  # net / the 2 orders that stayed sold
        self.assertEqual(d["cancelled_orders"], 1)
        pay = {p["payment_method"]: p for p in d["by_payment"]}
        self.assertEqual((pay["cash"]["orders"], pay["cash"]["total"]), (1, "4637.68"))
        self.assertEqual((pay["card"]["orders"], pay["card"]["total"]), (2, "1215.68"))
        self.assertEqual(d["by_order_type"][0]["order_type"], "counter")

    def test_date_ranges_are_respected(self):
        y = (timezone.localdate() - timedelta(days=1)).isoformat()
        d = self.get("reports/sales-summary/", **{"from": y, "to": y}).data
        self.assertEqual((d["orders"], d["total_sales"], d["net_sales"]), (1, "2318.84", "2318.84"))
        both = self.get("reports/sales-summary/", **{"from": y, "to": timezone.localdate().isoformat()}).data
        self.assertEqual(both["net_sales"], "7419.36")  # 5100.52 + 2318.84

    def test_discount_is_reported(self):
        shift = Shift.objects.create(cashier=self.mgr)
        res, _ = self.punch(user=self.mgr, shift=shift, discount_amount="100",
                            items=[{"price_id": self.m["large"].id, "quantity": 1}])
        client_for(self.mgr).post(f"/api/pos/orders/{res.data['id']}/settle/", {"payment_method": "card"}, format="json")
        self.assertEqual(self.get("reports/sales-summary/").data["discounts"], "100.00")

    def test_empty_range_is_all_zeros_not_an_error(self):
        d = self.get("reports/sales-summary/", **{"from": "2020-01-01", "to": "2020-01-31"}).data
        self.assertEqual((d["orders"], d["net_sales"], d["avg_order_value"]), (0, "0.00", "0.00"))

    def test_bad_dates_rejected(self):
        self.assertEqual(self.get("reports/sales-summary/", **{"from": "yesterday"}).status_code, 400)
        self.assertEqual(self.get("reports/sales-summary/", **{"from": "2026-02-10", "to": "2026-02-01"}).status_code, 400)
        self.assertEqual(self.get("reports/sales-summary/", **{"from": "2020-01-01", "to": "2026-01-01"}).status_code, 400)
        self.assertEqual(self.get("reports/hourly/", date="31-12-2026").status_code, 400)

    # ---- item sales ----
    def test_item_sales_is_net_of_refunds(self):
        d = self.get("reports/sales/").data
        rows = {(i["item_name"], i["size_label"]): i for i in d["items"]}
        self.assertEqual(set(rows), {("Fajita Pizza", "Large"), ("Fries", "")})  # refunded Small excluded
        self.assertEqual((rows[("Fajita Pizza", "Large")]["quantity"], rows[("Fajita Pizza", "Large")]["amount"]), (2, "3998.00"))
        self.assertEqual(rows[("Fajita Pizza", "Large")]["category"], "Pizza")
        self.assertEqual((d["total_quantity"], d["total_amount"]), (3, "4397.00"))
        self.assertEqual(d["items"][0]["item_name"], "Fajita Pizza", "best seller by amount first")

    def test_deal_sales_are_grouped_under_deals(self):
        res, _ = self.punch(items=[{"deal_id": self.m["deal"].id, "quantity": 1}])
        self._settle(res.data["id"], "card")
        deal = [i for i in self.get("reports/sales/").data["items"] if i["size_label"] == "Deal"][0]
        self.assertEqual((deal["category"], deal["amount"]), ("Deals", "999.00"))

    # ---- hourly ----
    def test_hourly_buckets_sum_to_net_sales(self):
        d = self.get("reports/hourly/").data
        self.assertEqual(len(d["hours"]), 24)
        self.assertEqual((d["total_orders"], d["total_sales"]), (2, "5100.52"))
        now_hour = timezone.localtime().hour
        self.assertGreaterEqual(d["hours"][now_hour]["orders"] + d["hours"][(now_hour - 1) % 24]["orders"], 2)

    # ---- cancellations ----
    def test_cancellation_report_splits_unmade_and_refunded(self):
        d = self.get("reports/cancellations/").data
        self.assertEqual([c["order_id"] for c in d["cancelled"]], [self.D])
        self.assertEqual((d["cancelled"][0]["cashier"], d["cancelled"][0]["total"]), ("alice", "462.84"))
        self.assertEqual(d["cancelled_total"], "462.84")
        self.assertEqual([(r["order_id"], r["reason"], r["total"]) for r in d["refunds"]], [(self.C, "cold food", "752.84")])
        self.assertEqual(d["refunds"][0]["refunded_by"], "mgr")

    # ---- dashboard ----
    def test_dashboard(self):
        d = self.get("dashboard/").data
        self.assertEqual(d["summary"]["net_sales"], "5100.52")
        self.assertEqual(d["previous_day_net_sales"], "2318.84")
        self.assertEqual(d["open_orders"], 1)  # E
        self.assertEqual(len(d["hourly"]), 24)
        self.assertEqual([(t["item_name"], t["quantity"]) for t in d["top_items"]], [("Fajita Pizza", 2), ("Fries", 1)])  # by quantity
        self.assertEqual(d["open_shifts"][0]["cashier"], "alice")
        self.assertEqual((d["open_shifts"][0]["orders"], d["open_shifts"][0]["sales"]), (3, "7419.36"))