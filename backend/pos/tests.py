import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from menu.testing import make_menu, reset_throttles
from .models import Order, Shift, StaffProfile

User = get_user_model()


def make_user(username, role):
    user = User.objects.create_user(username, password="pw")
    if role:
        StaffProfile.objects.create(user=user, role=role)
    return user


def client_for(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


class POSBase(APITestCase):
    def setUp(self):
        reset_throttles()
        self.m = make_menu()
        self.alice = make_user("alice", "cashier")
        self.bob = make_user("bob", "cashier")
        self.mgr = make_user("mgr", "manager")
        self.kitchen = make_user("kit", "kitchen")
        self.nobody = make_user("nobody", None)
        self.shift = Shift.objects.create(cashier=self.alice, opening_cash=1000)

    def punch(self, user=None, shift=None, items=None, **extra):
        body = {
            "client_order_id": str(uuid.uuid4()),
            "shift": (shift or self.shift).id,
            "order_type": "counter",
            "items": items if items is not None else [{"price_id": self.m["large"].id, "quantity": 1}],
            **extra,
        }
        return client_for(user or self.alice).post("/api/pos/orders/", body, format="json"), body


class AccessControlTests(POSBase):
    def test_anonymous_rejected(self):
        self.assertEqual(APIClient().get("/api/pos/orders/").status_code, 401)
        self.assertEqual(APIClient().post("/api/pos/shifts/open/", {}).status_code, 401)

    def test_user_without_staff_profile_rejected(self):
        c = client_for(self.nobody)
        self.assertEqual(c.get("/api/pos/orders/").status_code, 403)
        self.assertEqual(c.post("/api/pos/shifts/open/", {}, format="json").status_code, 403)

    def test_kitchen_can_read_but_not_take_money(self):
        c = client_for(self.kitchen)
        self.assertEqual(c.get("/api/pos/orders/").status_code, 200)
        res, _ = self.punch(user=self.kitchen)
        self.assertEqual(res.status_code, 403)

    def test_public_menu_still_open(self):
        self.assertEqual(APIClient().get("/api/menu-items/").status_code, 200)


class OrderPunchTests(POSBase):
    def test_server_computes_totals_and_ignores_client_money_fields(self):
        res, _ = self.punch(tax_amount="0", grand_total="1", subtotal="1",
                            items=[{"price_id": self.m["large"].id, "quantity": 2, "unit_price": "1"}])
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(Decimal(res.data["subtotal"]), Decimal("3998.00"))
        self.assertEqual(Decimal(res.data["tax_amount"]), Decimal("639.68"))
        self.assertEqual(Decimal(res.data["grand_total"]), Decimal("4637.68"))

    def test_deal_can_be_punched(self):
        res, _ = self.punch(items=[{"deal_id": self.m["deal"].id, "quantity": 1}])
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(Decimal(res.data["subtotal"]), Decimal("999.00"))

    def test_retry_with_same_client_order_id_does_not_duplicate(self):
        res1, body = self.punch()
        res2 = client_for(self.alice).post("/api/pos/orders/", body, format="json")
        self.assertEqual(res1.data["id"], res2.data["id"])
        self.assertEqual(Order.objects.count(), 1)

    def test_other_cashier_cannot_punch_on_my_shift_or_steal_an_order_id(self):
        res, body = self.punch(user=self.bob)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)
        self.punch()  # alice's order exists
        stolen = client_for(self.bob).post("/api/pos/orders/", body | {"client_order_id": str(Order.objects.get().client_order_id)}, format="json")
        self.assertEqual(stolen.status_code, 400)

    def test_cannot_punch_on_closed_shift(self):
        self.shift.status = "closed"
        self.shift.save()
        res, _ = self.punch()
        self.assertEqual(res.status_code, 400)

    def test_discount_rules(self):
        res, _ = self.punch(discount_amount="100")
        self.assertEqual(res.status_code, 400, "cashier may not discount")

        mshift = Shift.objects.create(cashier=self.mgr)
        res, _ = self.punch(user=self.mgr, shift=mshift, discount_amount="1999")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(Decimal(res.data["grand_total"]), Decimal("0.00"))

        res, _ = self.punch(user=self.mgr, shift=mshift, discount_amount="5000")
        self.assertEqual(res.status_code, 400, "discount can't exceed subtotal")
        res, _ = self.punch(user=self.mgr, shift=mshift, discount_amount="-5")
        self.assertEqual(res.status_code, 400)

    def test_bad_lines_rejected(self):
        for items in ([], [{"price_id": self.m["large"].id, "quantity": 0}], [{"price_id": 99999, "quantity": 1}]):
            res, _ = self.punch(items=items)
            self.assertEqual(res.status_code, 400, items)

    def test_cashier_list_is_scoped_to_own_shifts(self):
        self.punch()
        bshift = Shift.objects.create(cashier=self.bob)
        self.punch(user=self.bob, shift=bshift)
        self.assertEqual(len(client_for(self.alice).get("/api/pos/orders/").data), 1)
        self.assertEqual(len(client_for(self.mgr).get("/api/pos/orders/").data), 2)


class SettleRefundCancelTests(POSBase):
    def make_order(self):
        res, _ = self.punch()
        return res.data["id"], Decimal(res.data["grand_total"])  # 1999 + 319.84 = 2318.84

    def settle(self, user, oid, **body):
        return client_for(user).post(f"/api/pos/orders/{oid}/settle/", body, format="json")

    def test_cash_settle_with_change(self):
        oid, total = self.make_order()
        res = self.settle(self.alice, oid, payment_method="cash", amount_tendered="2500")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(Decimal(res.data["settlement"]["change_due"]), Decimal("2500") - total)

    def test_underpayment_and_missing_amount_rejected(self):
        oid, _ = self.make_order()
        self.assertEqual(self.settle(self.alice, oid, payment_method="cash", amount_tendered="10").status_code, 400)
        self.assertEqual(self.settle(self.alice, oid, payment_method="cash").status_code, 400)
        self.assertEqual(self.settle(self.alice, oid, payment_method="cash", amount_tendered="-5").status_code, 400)

    def test_card_charges_exact_total_with_no_change(self):
        oid, total = self.make_order()
        res = self.settle(self.alice, oid, payment_method="card", amount_tendered="99999")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Decimal(res.data["settlement"]["amount_tendered"]), total)
        self.assertEqual(Decimal(res.data["settlement"]["change_due"]), 0)

    def test_double_settle_is_a_clean_400_not_a_500(self):
        oid, _ = self.make_order()
        self.assertEqual(self.settle(self.alice, oid, payment_method="card").status_code, 200)
        self.assertEqual(self.settle(self.alice, oid, payment_method="card").status_code, 400)

    def test_other_cashier_cannot_settle_or_cancel(self):
        oid, _ = self.make_order()
        self.assertEqual(self.settle(self.bob, oid, payment_method="card").status_code, 403)
        self.assertEqual(client_for(self.bob).post(f"/api/pos/orders/{oid}/cancel/").status_code, 403)
        self.assertEqual(self.settle(self.mgr, oid, payment_method="card").status_code, 200, "manager may")

    def test_refund_needs_manager_and_settled_order(self):
        oid, _ = self.make_order()
        url = f"/api/pos/orders/{oid}/refund/"
        self.assertEqual(client_for(self.mgr).post(url, {}, format="json").status_code, 400, "unsettled")
        self.settle(self.alice, oid, payment_method="card")
        self.assertEqual(client_for(self.alice).post(url, {}, format="json").status_code, 403, "cashier")
        res = client_for(self.mgr).post(url, {"reason": "wrong item"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.data["order"]["status"], "refunded")
        self.assertEqual(client_for(self.mgr).post(url, {}, format="json").status_code, 400, "twice")

    def test_unknown_order_is_404(self):
        self.assertEqual(self.settle(self.alice, 99999, payment_method="card").status_code, 404)


class ShiftTests(POSBase):
    def test_open_shift_validation_and_single_open_shift(self):
        c = client_for(self.bob)
        self.assertEqual(c.post("/api/pos/shifts/open/", {"opening_cash": "abc"}, format="json").status_code, 400)
        self.assertEqual(c.post("/api/pos/shifts/open/", {"opening_cash": "-1"}, format="json").status_code, 400)
        self.assertEqual(c.post("/api/pos/shifts/open/", {"opening_cash": "500"}, format="json").status_code, 201)
        self.assertEqual(c.post("/api/pos/shifts/open/", {"opening_cash": "500"}, format="json").status_code, 400)

    def test_close_blocked_by_open_orders_then_allowed(self):
        res, _ = self.punch()
        url = f"/api/pos/shifts/{self.shift.id}/close/"
        c = client_for(self.alice)
        self.assertEqual(c.post(url, {"closing_cash": "100"}, format="json").status_code, 400)
        c.post(f"/api/pos/orders/{res.data['id']}/cancel/")
        self.assertEqual(c.post(url, {"closing_cash": "abc"}, format="json").status_code, 400)
        self.assertEqual(c.post(url, {"closing_cash": "1200"}, format="json").status_code, 200)

    def test_current_shift(self):
        self.assertEqual(client_for(self.alice).get("/api/pos/shifts/current/").status_code, 200)
        self.assertEqual(client_for(self.bob).get("/api/pos/shifts/current/").status_code, 404)

    def test_jwt_login_works_for_staff(self):
        res = APIClient().post("/api/pos/auth/login/", {"username": "alice", "password": "pw"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.data)
