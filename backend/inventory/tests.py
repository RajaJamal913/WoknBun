import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from pos.models import StaffProfile
from .models import PurchaseInvoice, PurchaseInvoiceLine, RawMaterial, StockMovement, Supplier, Warehouse, default_warehouse
from .services import stock_on_hand

User = get_user_model()


def staff(username, role):
    u = User.objects.create_user(username, password="pw")
    StaffProfile.objects.create(user=u, role=role)
    c = APIClient()
    c.force_authenticate(u)
    return u, c


class InvBase(APITestCase):
    def setUp(self):
        self.mgr, self.m = staff("mgr", "manager")
        self.cashier, self.c = staff("cash", "cashier")
        self.kitchen, self.k = staff("kit", "kitchen")

    def material(self, name="Flour", stock_unit="g", purchase_unit="kg", factor="1000", opening=None, **extra):
        body = {"name": name, "stock_unit": stock_unit, "purchase_unit": purchase_unit, "purchase_factor": factor, **extra}
        if opening is not None:
            body["opening_stock"] = opening
        res = self.m.post("/api/inventory/materials/", body, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        return res.data

    def supplier(self, name="Metro"):
        res = self.m.post("/api/inventory/suppliers/", {"name": name}, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        return res.data

    def buy(self, supplier, lines, **extra):
        body = {"supplier": supplier["id"], "client_ref": str(uuid.uuid4()), "lines": lines, **extra}
        return self.m.post("/api/inventory/purchase-invoices/", body, format="json")


class AccessTests(InvBase):
    PATHS = ["materials/", "suppliers/", "purchase-invoices/", "reports/stock-summary/"]

    def test_only_managers_may_use_inventory(self):
        for p in self.PATHS:
            self.assertEqual(self.m.get(f"/api/inventory/{p}").status_code, 200, p)
            for who in (self.c, self.k, APIClient()):
                self.assertIn(who.get(f"/api/inventory/{p}").status_code, (401, 403), p)

    def test_cashier_cannot_post_a_purchase(self):
        res = self.c.post("/api/inventory/materials/", {"name": "X", "stock_unit": "g", "purchase_unit": "kg"}, format="json")
        self.assertEqual(res.status_code, 403)


class MaterialTests(InvBase):
    def test_opening_stock_creates_a_ledger_row_and_shows_on_hand(self):
        mat = self.material(opening="2500")
        self.assertEqual(Decimal(mat["stock_on_hand"]), Decimal("2500"))
        mv = StockMovement.objects.get()
        self.assertEqual((mv.movement_type, mv.quantity, mv.warehouse_id), ("opening", Decimal("2500.000"), default_warehouse().id))

    def test_duplicate_names_rejected_case_insensitively(self):
        self.material("Flour")
        res = self.m.post("/api/inventory/materials/", {"name": "flour", "stock_unit": "g", "purchase_unit": "kg"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_stock_unit_is_locked_once_there_is_history_but_the_buying_side_is_not(self):
        mat = self.material(opening="10")
        url = f"/api/inventory/materials/{mat['id']}/"
        self.assertEqual(self.m.patch(url, {"stock_unit": "kg"}, format="json").status_code, 400)
        res = self.m.patch(url, {"reorder_level": "300", "purchase_unit": "bag", "purchase_factor": "25000"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(Decimal(res.data["purchase_factor"]), Decimal("25000"))
        self.assertEqual(Decimal(res.data["stock_on_hand"]), Decimal("10"), "stock is untouched")

    def test_changing_the_factor_only_affects_future_purchases(self):
        flour, sup = self.material(), self.supplier()
        self.buy(sup, [{"material": flour["id"], "quantity": "1", "unit_price": "100"}])           # 1 kg = 1000 g
        self.m.patch(f"/api/inventory/materials/{flour['id']}/", {"purchase_factor": "500"}, format="json")
        self.buy(sup, [{"material": flour["id"], "quantity": "1", "unit_price": "100"}])           # now 1 kg = 500 g
        self.assertEqual(stock_on_hand(RawMaterial.objects.get()), Decimal("1500"))
        self.assertEqual(sorted(PurchaseInvoiceLine.objects.values_list("stock_quantity", flat=True)), [Decimal("500"), Decimal("1000")])

    def test_a_number_is_not_a_unit_and_a_bad_existing_unit_can_be_repaired(self):
        res = self.m.post("/api/inventory/materials/", {"name": "Flour", "stock_unit": "500", "purchase_unit": "1"}, format="json")
        self.assertEqual(res.status_code, 400)
        # a record saved before this check existed, with history behind it
        bad = RawMaterial.objects.create(name="Old", stock_unit="500", purchase_unit="1", purchase_factor=500)
        StockMovement.objects.create(warehouse=default_warehouse(), material=bad, quantity=500, movement_type="opening")
        url = f"/api/inventory/materials/{bad.id}/"
        self.assertEqual(self.m.patch(url, {"stock_unit": "123"}, format="json").status_code, 400, "still not a unit")
        res = self.m.patch(url, {"stock_unit": "g", "purchase_unit": "kg", "purchase_factor": "1000"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual((res.data["stock_unit"], res.data["purchase_unit"]), ("g", "kg"))
        self.assertEqual(self.m.patch(url, {"stock_unit": "kg"}, format="json").status_code, 400, "now it is locked")

    def test_units_can_change_before_any_stock_exists(self):
        mat = self.material()
        res = self.m.patch(f"/api/inventory/materials/{mat['id']}/", {"purchase_factor": "500"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)

    def test_bad_factor_rejected(self):
        res = self.m.post("/api/inventory/materials/", {"name": "X", "stock_unit": "g", "purchase_unit": "kg", "purchase_factor": "0"}, format="json")
        self.assertEqual(res.status_code, 400)


class PurchaseTests(InvBase):
    def test_purchase_converts_units_and_adds_stock(self):
        flour, sup = self.material(), self.supplier()
        res = self.buy(sup, [{"material": flour["id"], "quantity": "25", "unit_price": "180.50"}], paid_now="1000")
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.data["total"], "4512.50")           # 25 kg x 180.50
        self.assertEqual(res.data["amount_paid"], "1000.00")
        self.assertEqual(res.data["balance_due"], "3512.50")
        self.assertEqual(stock_on_hand(RawMaterial.objects.get()), Decimal("25000"))   # 25 kg = 25,000 g
        mv = StockMovement.objects.get()
        self.assertEqual(mv.unit_cost, Decimal("0.1805"))                              # Rs per gram

    def test_retry_with_same_client_ref_does_not_double_stock_or_bill(self):
        flour, sup = self.material(), self.supplier()
        ref = str(uuid.uuid4())
        for expected in (201, 200):
            res = self.m.post("/api/inventory/purchase-invoices/", {
                "supplier": sup["id"], "client_ref": ref, "lines": [{"material": flour["id"], "quantity": "1", "unit_price": "100"}]}, format="json")
            self.assertEqual(res.status_code, expected)
        self.assertEqual(PurchaseInvoice.objects.count(), 1)
        self.assertEqual(stock_on_hand(RawMaterial.objects.get()), Decimal("1000"))

    def test_validation(self):
        flour, sup = self.material(), self.supplier()
        line = {"material": flour["id"], "quantity": "1", "unit_price": "100"}
        self.assertEqual(self.buy(sup, []).status_code, 400)
        self.assertEqual(self.buy(sup, [{**line, "quantity": "0"}]).status_code, 400)
        self.assertEqual(self.buy(sup, [{**line, "unit_price": "-1"}]).status_code, 400)
        self.assertEqual(self.buy(sup, [line], paid_now="101").status_code, 400, "can't pay more than the total")
        self.assertEqual(self.buy(sup, [line], invoice_date="2999-01-01").status_code, 400)
        self.m.patch(f"/api/inventory/materials/{flour['id']}/", {"is_active": False}, format="json")
        self.assertEqual(self.buy(sup, [line]).status_code, 400, "retired material")
        self.assertEqual(PurchaseInvoice.objects.count(), 0)
        self.assertEqual(StockMovement.objects.count(), 0, "a rejected bill leaves no stock behind")

    def test_payments_and_supplier_balance(self):
        flour, sup = self.material(), self.supplier()
        inv = self.buy(sup, [{"material": flour["id"], "quantity": "10", "unit_price": "100"}]).data     # 1000 due
        self.assertEqual(self.m.get("/api/inventory/suppliers/").data[0]["balance_due"], "1000.00")
        res = self.m.post(f"/api/inventory/purchase-invoices/{inv['id']}/payments/", {"amount": "400"}, format="json")
        self.assertEqual((res.status_code, res.data["balance_due"]), (200, "600.00"))
        too_much = self.m.post(f"/api/inventory/purchase-invoices/{inv['id']}/payments/", {"amount": "601"}, format="json")
        self.assertEqual(too_much.status_code, 400)
        self.m.post(f"/api/inventory/purchase-invoices/{inv['id']}/payments/", {"amount": "600", "method": "bank"}, format="json")
        self.assertEqual(self.m.get("/api/inventory/suppliers/").data[0]["balance_due"], "0.00")
        self.assertEqual(len(self.m.get(f"/api/inventory/purchase-invoices/{inv['id']}/").data["payments"]), 2)

    def test_void_reverses_stock_blocks_payments_and_cannot_repeat(self):
        flour, sup = self.material(opening="500"), self.supplier()
        inv = self.buy(sup, [{"material": flour["id"], "quantity": "2", "unit_price": "100"}], paid_now="50").data
        self.assertEqual(stock_on_hand(RawMaterial.objects.get()), Decimal("2500"))
        res = self.m.post(f"/api/inventory/purchase-invoices/{inv['id']}/void/", {"reason": "wrong supplier"}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.data["status"], "void")
        self.assertIn("already paid", res.data["warning"])
        self.assertEqual(stock_on_hand(RawMaterial.objects.get()), Decimal("500"))
        self.assertEqual(StockMovement.objects.filter(movement_type="purchase_void").count(), 1)
        self.assertEqual(StockMovement.objects.count(), 3, "history is kept: opening, purchase, void")
        self.assertEqual(self.m.post(f"/api/inventory/purchase-invoices/{inv['id']}/void/", {"reason": "again"}, format="json").status_code, 400)
        self.assertEqual(self.m.post(f"/api/inventory/purchase-invoices/{inv['id']}/payments/", {"amount": "10"}, format="json").status_code, 400)
        self.assertEqual(self.m.get("/api/inventory/suppliers/").data[0]["balance_due"], "0.00", "void bills are not owed")
        self.assertEqual(self.m.post(f"/api/inventory/purchase-invoices/{inv['id']}/void/", {"reason": " "}, format="json").status_code, 400)


class ReportTests(InvBase):
    def test_stock_summary_low_flag_value_and_purchase_unit(self):
        flour, sup = self.material(reorder_level="5000"), self.supplier()
        self.material("Cooking oil", "ml", "litre", "1000")
        self.buy(sup, [{"material": flour["id"], "quantity": "4", "unit_price": "200"}])       # 4 kg = 4000 g at Rs 0.2/g
        d = self.m.get("/api/inventory/reports/stock-summary/").data
        row = {r["name"]: r for r in d["materials"]}["Flour"]
        self.assertEqual((row["on_hand"], row["on_hand_purchase"], row["low"], row["value"]), ("4000", "4", True, "800.00"))
        self.assertEqual(d["low_count"], 1)
        self.assertEqual(d["total_value"], "800.00")

    def test_last_cost_ignores_a_voided_purchase(self):
        flour, sup = self.material(), self.supplier()
        self.buy(sup, [{"material": flour["id"], "quantity": "1", "unit_price": "100"}])
        bad = self.buy(sup, [{"material": flour["id"], "quantity": "1", "unit_price": "999"}]).data
        self.m.post(f"/api/inventory/purchase-invoices/{bad['id']}/void/", {"reason": "typo"}, format="json")
        row = self.m.get("/api/inventory/reports/stock-summary/").data["materials"][0]
        self.assertEqual(row["last_cost"], "0.1000")

    def test_stock_ledger_has_running_balance(self):
        flour, sup = self.material(opening="100"), self.supplier()
        inv = self.buy(sup, [{"material": flour["id"], "quantity": "1", "unit_price": "100"}]).data
        self.m.post(f"/api/inventory/purchase-invoices/{inv['id']}/void/", {"reason": "x"}, format="json")
        d = self.m.get(f"/api/inventory/reports/stock-ledger/?material={flour['id']}").data
        self.assertEqual([(r["label"], r["qty_in"], r["qty_out"], r["balance"]) for r in d["rows"]], [
            ("Opening stock", "100", "", "100"), ("Purchase", "1000", "", "1100"), ("Purchase voided", "", "1000", "100")])
        self.assertEqual((d["opening"], d["total_in"], d["total_out"], d["closing"]), ("0", "1100", "1000", "100"))
        self.assertEqual(self.m.get("/api/inventory/reports/stock-ledger/").status_code, 400)

    def test_stock_ledger_opening_balance_carries_in_from_earlier_days(self):
        from datetime import timedelta
        from django.utils import timezone
        flour = self.material(opening="100")
        StockMovement.objects.update(created_at=timezone.now() - timedelta(days=3))
        today = timezone.localdate().isoformat()
        d = self.m.get(f"/api/inventory/reports/stock-ledger/?material={flour['id']}&from={today}&to={today}").data
        self.assertEqual((d["opening"], d["closing"], d["rows"]), ("100", "100", []))

    def test_purchase_report_totals_exclude_void(self):
        flour = self.material()
        a, b = self.supplier("A"), self.supplier("B")
        self.buy(a, [{"material": flour["id"], "quantity": "1", "unit_price": "100"}], paid_now="100")
        voided = self.buy(a, [{"material": flour["id"], "quantity": "1", "unit_price": "500"}]).data
        self.m.post(f"/api/inventory/purchase-invoices/{voided['id']}/void/", {"reason": "x"}, format="json")
        self.buy(b, [{"material": flour["id"], "quantity": "2", "unit_price": "100"}])
        d = self.m.get("/api/inventory/reports/purchases/").data
        self.assertEqual((d["count"], d["total"], d["paid"], d["due"], d["voided_count"]), (2, "300.00", "100.00", "200.00", 1))
        self.assertEqual(len(d["invoices"]), 3)
        only_b = self.m.get(f"/api/inventory/reports/purchases/?supplier={b['id']}").data
        self.assertEqual((only_b["count"], only_b["total"]), (1, "200.00"))
        self.assertEqual(self.m.get("/api/inventory/reports/purchases/?from=2026-02-01&to=2026-01-01").status_code, 400)


class WarehouseTests(InvBase):
    def test_a_single_default_warehouse_is_created_on_demand(self):
        self.material(opening="1")
        self.material("Salt", opening="1")
        self.assertEqual(Warehouse.objects.count(), 1)
        self.assertTrue(Warehouse.objects.get().is_default)


# ---------------------------------------------------------------- Phase 2: recipes, deals, automatic stock use
import uuid
from unittest import mock

from menu.models import Category, Deal, MenuItem, MenuItemPrice
from pos.models import Shift
from .models import DealComponent, RecipeLine


class RecipeBase(InvBase):
    def setUp(self):
        super().setUp()
        cat = Category.objects.create(name="Mains")
        self.burger = MenuItem.objects.create(category=cat, name="Zinger Burger")
        self.single = MenuItemPrice.objects.create(menu_item=self.burger, label="Single", price="500")
        self.double = MenuItemPrice.objects.create(menu_item=self.burger, label="Double", price="800")
        self.fries_item = MenuItem.objects.create(category=cat, name="Fries")
        self.fries = MenuItemPrice.objects.create(menu_item=self.fries_item, label="", price="200")
        self.plain = MenuItem.objects.create(category=cat, name="Water")
        self.water = MenuItemPrice.objects.create(menu_item=self.plain, label="", price="50")
        self.deal = Deal.objects.create(name="Combo", description="burger + fries", price="650")

        self.chicken = RawMaterial.objects.get(pk=self.material("Chicken", "g", "kg", "1000", opening="10000")["id"])
        self.potato = RawMaterial.objects.get(pk=self.material("Potato", "g", "kg", "1000", opening="5000")["id"])
        self.shift = Shift.objects.create(cashier=self.cashier, opening_cash=0)

    def set_recipe(self, price, lines):
        res = self.m.put(f"/api/inventory/recipes/{price.id}/",
                         {"lines": [{"material": m.id, "quantity": str(q)} for m, q in lines]}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        return res.data

    def set_deal(self, comps):
        res = self.m.put(f"/api/inventory/deals/{self.deal.id}/contents/",
                         {"components": [{"price": p.id, "quantity": q} for p, q in comps]}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        return res.data

    def on_hand(self, m):
        return stock_on_hand(m)

    def punch_and_settle(self, items):
        res = self.c.post("/api/pos/orders/", {"client_order_id": str(uuid.uuid4()), "shift": self.shift.id,
                                               "order_type": "counter", "items": items}, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        oid = res.data["id"]
        s = self.c.post(f"/api/pos/orders/{oid}/settle/", {"payment_method": "card"}, format="json")
        self.assertEqual(s.status_code, 200, s.content)
        return oid

    def recipes_set(self):
        self.set_recipe(self.single, [(self.chicken, 120)])
        self.set_recipe(self.double, [(self.chicken, 240)])
        self.set_recipe(self.fries, [(self.potato, 150)])


class RecipeApiTests(RecipeBase):
    def test_only_managers(self):
        self.assertEqual(self.c.get("/api/inventory/recipes/").status_code, 403)
        self.assertEqual(self.k.put(f"/api/inventory/recipes/{self.single.id}/", {"lines": []}, format="json").status_code, 403)

    def test_recipe_roundtrip_replaces_and_clears(self):
        data = self.set_recipe(self.single, [(self.chicken, 120), (self.potato, "10.5")])
        size = [s for i in data["items"] if i["id"] == self.burger.id for s in i["sizes"] if s["price_id"] == self.single.id][0]
        self.assertEqual([(l["material_name"], l["quantity"]) for l in size["lines"]], [("Chicken", "120"), ("Potato", "10.5")])
        self.set_recipe(self.single, [(self.chicken, 100)])
        self.assertEqual(RecipeLine.objects.filter(price=self.single).count(), 1)
        self.set_recipe(self.single, [])
        self.assertEqual(RecipeLine.objects.filter(price=self.single).count(), 0)

    def test_bad_recipes_rejected(self):
        url = f"/api/inventory/recipes/{self.single.id}/"
        dup = {"lines": [{"material": self.chicken.id, "quantity": "1"}, {"material": self.chicken.id, "quantity": "2"}]}
        self.assertEqual(self.m.put(url, dup, format="json").status_code, 400)
        self.assertEqual(self.m.put(url, {"lines": [{"material": self.chicken.id, "quantity": "0"}]}, format="json").status_code, 400)
        self.assertEqual(self.m.put(url, {"lines": [{"material": 99999, "quantity": "1"}]}, format="json").status_code, 400)
        self.assertEqual(self.m.put("/api/inventory/recipes/99999/", {"lines": []}, format="json").status_code, 404)
        self.chicken.is_active = False
        self.chicken.save()
        self.assertEqual(self.m.put(url, {"lines": [{"material": self.chicken.id, "quantity": "5"}]}, format="json").status_code, 400)

    def test_cost_and_margin_use_latest_purchase_cost(self):
        sup = self.supplier()
        body = {"supplier": sup["id"], "invoice_date": "2026-10-01", "client_ref": str(uuid.uuid4()),
                "lines": [{"material": self.chicken.id, "quantity": "1", "unit_price": "800"}]}   # Rs 800 per kg = 0.8 per g
        self.assertEqual(self.m.post("/api/inventory/purchase-invoices/", body, format="json").status_code, 201)
        data = self.set_recipe(self.single, [(self.chicken, 120)])
        size = [s for i in data["items"] if i["id"] == self.burger.id for s in i["sizes"] if s["price_id"] == self.single.id][0]
        self.assertEqual((size["cost"], size["margin"], size["margin_pct"], size["cost_complete"]), ("96.00", "404.00", "80.8", True))
        data = self.set_recipe(self.double, [(self.chicken, 100), (self.potato, 50)])        # potato never bought: cost unknown
        size = [s for i in data["items"] if i["id"] == self.burger.id for s in i["sizes"] if s["price_id"] == self.double.id][0]
        self.assertEqual((size["cost"], size["cost_complete"]), ("80.00", False))
        self.assertEqual(data["coverage"], {"sizes": 4, "with_recipe": 2})

    def test_recipe_with_no_purchase_price_has_no_cost_rather_than_zero(self):
        data = self.set_recipe(self.single, [(self.chicken, 120)])          # chicken has opening stock but was never bought
        size = [s for i in data["items"] if i["id"] == self.burger.id for s in i["sizes"] if s["price_id"] == self.single.id][0]
        self.assertEqual((size["has_recipe"], size["cost"], size["margin"]), (True, None, None))

    def test_deal_contents_and_cost(self):
        self.set_recipe(self.single, [(self.chicken, 100)])
        data = self.set_deal([(self.single, 1), (self.fries, 2)])
        deal = data["deals"][0]
        self.assertEqual([(c["item_name"], c["quantity"], c["has_recipe"]) for c in deal["components"]],
                         [("Zinger Burger", 1, True), ("Fries", 2, False)])
        self.assertFalse(deal["cost_complete"])                      # fries has no recipe yet
        dup = {"components": [{"price": self.single.id, "quantity": 1}, {"price": self.single.id, "quantity": 2}]}
        self.assertEqual(self.m.put(f"/api/inventory/deals/{self.deal.id}/contents/", dup, format="json").status_code, 400)
        self.assertEqual(self.m.put("/api/inventory/deals/9999/contents/", {"components": []}, format="json").status_code, 404)


class SaleStockTests(RecipeBase):
    def test_settle_takes_ingredients_out_and_refund_puts_them_back(self):
        self.recipes_set()
        oid = self.punch_and_settle([{"price_id": self.double.id, "quantity": 2}, {"price_id": self.fries.id, "quantity": 3}])
        self.assertEqual(self.on_hand(self.chicken), Decimal("10000") - 240 * 2)
        self.assertEqual(self.on_hand(self.potato), Decimal("5000") - 450)
        row = StockMovement.objects.get(material=self.chicken, movement_type="sale")
        self.assertEqual((row.reference_type, row.reference_id), ("pos_order", oid))

        self.assertEqual(self.m.post(f"/api/pos/orders/{oid}/refund/", {"reason": "cold"}, format="json").status_code, 200)
        self.assertEqual(self.on_hand(self.chicken), Decimal("10000"))
        self.assertEqual(self.on_hand(self.potato), Decimal("5000"))

    def test_open_or_cancelled_orders_do_not_touch_stock(self):
        self.recipes_set()
        res = self.c.post("/api/pos/orders/", {"client_order_id": str(uuid.uuid4()), "shift": self.shift.id, "order_type": "counter",
                                               "items": [{"price_id": self.single.id, "quantity": 1}]}, format="json")
        self.assertEqual(self.on_hand(self.chicken), Decimal("10000"))
        self.c.post(f"/api/pos/orders/{res.data['id']}/cancel/", {"reason": "x"}, format="json")
        self.assertEqual(self.on_hand(self.chicken), Decimal("10000"))

    def test_deal_uses_each_components_recipe(self):
        self.recipes_set()
        self.set_deal([(self.single, 2), (self.fries, 1)])
        self.punch_and_settle([{"deal_id": self.deal.id, "quantity": 3}])
        self.assertEqual(self.on_hand(self.chicken), Decimal("10000") - 120 * 2 * 3)
        self.assertEqual(self.on_hand(self.potato), Decimal("5000") - 150 * 3)

    def test_items_without_recipe_sell_normally_and_use_nothing(self):
        before = StockMovement.objects.count()
        self.punch_and_settle([{"price_id": self.water.id, "quantity": 2}])
        self.punch_and_settle([{"deal_id": self.deal.id, "quantity": 1}])     # deal with no contents yet
        self.assertEqual(StockMovement.objects.count(), before)

    def test_deduct_and_reverse_are_idempotent(self):
        from pos.models import Order
        from . import consumption
        self.recipes_set()
        oid = self.punch_and_settle([{"price_id": self.single.id, "quantity": 1}])
        order = Order.objects.get(pk=oid)
        self.assertFalse(consumption.deduct_for_sale(order, self.cashier))
        self.assertEqual(self.on_hand(self.chicken), Decimal("9880"))
        self.assertTrue(consumption.reverse_for_sale(order, self.cashier))
        self.assertFalse(consumption.reverse_for_sale(order, self.cashier))
        self.assertEqual(self.on_hand(self.chicken), Decimal("10000"))

    def test_a_stock_failure_never_blocks_the_sale(self):
        self.recipes_set()
        with mock.patch("inventory.consumption.deduct_for_sale", side_effect=RuntimeError("boom")):
            with self.assertLogs("inventory.consumption", level="ERROR"):
                oid = self.punch_and_settle([{"price_id": self.single.id, "quantity": 1}])
        from pos.models import Order
        self.assertEqual(Order.objects.get(pk=oid).status, "settled")
        self.assertEqual(self.on_hand(self.chicken), Decimal("10000"))

    def test_sale_cost_is_recorded_from_latest_purchase(self):
        sup = self.supplier()
        self.m.post("/api/inventory/purchase-invoices/", {"supplier": sup["id"], "invoice_date": "2026-10-01", "client_ref": str(uuid.uuid4()),
                    "lines": [{"material": self.chicken.id, "quantity": "1", "unit_price": "800"}]}, format="json")
        self.recipes_set()
        self.punch_and_settle([{"price_id": self.single.id, "quantity": 1}])
        self.assertEqual(StockMovement.objects.get(material=self.chicken, movement_type="sale").unit_cost, Decimal("0.8000"))


class OnlineSaleStockTests(RecipeBase):
    def web_order(self):
        from orders.models import Order as Web, OrderItem as WebItem
        w = Web.objects.create(full_name="Sara", mobile_number="03001234567", address_line="H1", subtotal=500, tax_amount=0, grand_total=500)
        WebItem.objects.create(order=w, item_name="Zinger Burger", size_label="Single", unit_price=500, quantity=2, line_total=1000,
                               menu_item=self.burger, price=self.single)
        return w

    def act(self, w, action, **body):
        res = self.c.post(f"/api/pos/online-orders/{w.id}/{action}/", body, format="json")
        self.assertEqual(res.status_code, 200, res.content)

    def test_accept_deducts_once_deliver_does_not_repeat_and_cancel_returns(self):
        self.recipes_set()
        w = self.web_order()
        self.act(w, "accept")
        self.assertEqual(self.on_hand(self.chicken), Decimal("10000") - 240)
        self.act(w, "deliver")
        self.assertEqual(self.on_hand(self.chicken), Decimal("10000") - 240)

        w2 = self.web_order()
        self.act(w2, "accept")
        self.assertEqual(self.on_hand(self.chicken), Decimal("10000") - 480)
        self.act(w2, "cancel", reason="customer called")
        self.assertEqual(self.on_hand(self.chicken), Decimal("10000") - 240)


class AdjustmentTests(InvBase):
    def adjust(self, material, **extra):
        body = {"client_ref": str(uuid.uuid4()), "material": material["id"], "kind": "wastage", "direction": "out",
                "quantity": "500", "reason": "Expired", **extra}
        return self.m.post("/api/inventory/adjustments/", body, format="json")

    def on_hand(self, material):
        return stock_on_hand(RawMaterial.objects.get(pk=material["id"]))

    def test_wastage_takes_stock_out_and_leaves_a_ledger_row(self):
        mat = self.material(opening="5000")
        res = self.adjust(mat)
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(self.on_hand(mat), Decimal("4500"))
        mv = StockMovement.objects.get(material_id=mat["id"], movement_type="wastage")
        self.assertEqual((mv.quantity, mv.note), (Decimal("-500.000"), "Expired"))

    def test_a_retried_adjustment_is_saved_once(self):
        mat = self.material(opening="5000")
        ref = str(uuid.uuid4())
        self.assertEqual(self.adjust(mat, client_ref=ref).status_code, 201)
        self.assertEqual(self.adjust(mat, client_ref=ref).status_code, 200)
        self.assertEqual(self.on_hand(mat), Decimal("4500"))

    def test_cannot_take_out_more_than_is_in_stock(self):
        mat = self.material(opening="100")
        res = self.adjust(mat, quantity="500")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(self.on_hand(mat), Decimal("100"))

    def test_a_correction_can_add_stock_but_wastage_cannot(self):
        mat = self.material(opening="100")
        self.assertEqual(self.adjust(mat, kind="adjustment", direction="in", quantity="50", reason="Found extra").status_code, 201)
        self.assertEqual(self.on_hand(mat), Decimal("150"))
        self.assertEqual(self.adjust(mat, kind="wastage", direction="in").status_code, 400)

    def test_a_reason_is_required(self):
        mat = self.material(opening="100")
        self.assertEqual(self.adjust(mat, reason=" ").status_code, 400)

    def test_cashier_cannot_adjust_stock(self):
        mat = self.material(opening="100")
        res = self.c.post("/api/inventory/adjustments/", {"material": mat["id"], "kind": "wastage", "direction": "out",
                          "quantity": "5", "reason": "Expired"}, format="json")
        self.assertEqual(res.status_code, 403)


class StockCountTests(InvBase):
    def count(self, lines, **extra):
        return self.m.post("/api/inventory/stock-counts/", {"client_ref": str(uuid.uuid4()), "lines": lines, **extra}, format="json")

    def test_a_count_sets_stock_to_what_was_counted(self):
        mat = self.material(opening="5000")
        res = self.count([{"material": mat["id"], "counted": "4700"}])
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(stock_on_hand(RawMaterial.objects.get(pk=mat["id"])), Decimal("4700"))
        self.assertEqual(res.data["differing"], 1)
        line = res.data["lines"][0]
        self.assertEqual((line["expected"], line["counted"], line["difference"]), ("5000", "4700", "-300"))

    def test_only_the_difference_is_written_and_matching_items_write_nothing(self):
        a, b = self.material("Flour", opening="1000"), self.material("Sugar", opening="1000")
        self.count([{"material": a["id"], "counted": "1000"}, {"material": b["id"], "counted": "900"}])
        self.assertFalse(StockMovement.objects.filter(material_id=a["id"], movement_type="count").exists())
        self.assertEqual(StockMovement.objects.get(material_id=b["id"], movement_type="count").quantity, Decimal("-100.000"))

    def test_a_retried_count_is_posted_once(self):
        mat = self.material(opening="1000")
        body = {"client_ref": str(uuid.uuid4()), "lines": [{"material": mat["id"], "counted": "900"}]}
        self.assertEqual(self.m.post("/api/inventory/stock-counts/", body, format="json").status_code, 201)
        self.assertEqual(self.m.post("/api/inventory/stock-counts/", body, format="json").status_code, 200)
        self.assertEqual(stock_on_hand(RawMaterial.objects.get(pk=mat["id"])), Decimal("900"))

    def test_loss_is_valued_at_the_last_purchase_cost(self):
        mat = self.material("Flour")
        self.assertEqual(self.buy(self.supplier(), [{"material": mat["id"], "quantity": "2", "unit_price": "100"}]).status_code, 201)
        res = self.count([{"material": mat["id"], "counted": "1900"}])      # 2 kg bought at Rs 100/kg = Rs 0.10 per g
        self.assertEqual(res.data["loss_value"], "10.00")
        self.assertEqual(res.data["gain_value"], "0.00")

    def test_an_item_never_bought_cannot_be_valued_but_is_still_counted(self):
        mat = self.material("Salt", opening="1000")
        res = self.count([{"material": mat["id"], "counted": "800"}])
        self.assertEqual(res.data["unknown_cost_lines"], 1)
        self.assertIsNone(res.data["lines"][0]["value"])

    def test_the_same_item_twice_is_refused(self):
        mat = self.material(opening="1000")
        self.assertEqual(self.count([{"material": mat["id"], "counted": "1"}, {"material": mat["id"], "counted": "2"}]).status_code, 400)


class AlertAndDateTests(InvBase):
    def test_alerts_count_items_at_or_below_their_reorder_level(self):
        self.material("Flour", opening="500", reorder_level="1000")
        self.material("Sugar", opening="5000", reorder_level="1000")
        self.assertEqual(self.m.get("/api/inventory/alerts/").json(), {"low_count": 1})
        self.assertEqual(self.c.get("/api/inventory/alerts/").status_code, 403)

    def test_opening_stock_can_be_dated_to_the_day_it_was_bought(self):
        from datetime import timedelta
        from django.utils import timezone
        day = timezone.localdate() - timedelta(days=3)
        mat = self.material("Rice", opening="5000", opening_date=day.isoformat())
        mv = StockMovement.objects.get(material_id=mat["id"], movement_type="opening")
        self.assertEqual(timezone.localtime(mv.created_at).date(), day)
        row = next(r for r in self.m.get("/api/inventory/reports/stock-summary/").json()["materials"] if r["id"] == mat["id"])
        self.assertEqual(row["last_bought"], day.isoformat())

    def test_opening_date_cannot_be_in_the_future(self):
        from datetime import timedelta
        from django.utils import timezone
        tomorrow = (timezone.localdate() + timedelta(days=1)).isoformat()
        res = self.m.post("/api/inventory/materials/", {"name": "Oil", "stock_unit": "ml", "purchase_unit": "litre",
                          "purchase_factor": "1000", "opening_stock": "1000", "opening_date": tomorrow}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_last_bought_follows_the_bill_date_not_the_day_it_was_typed_in(self):
        from datetime import timedelta
        from django.utils import timezone
        mat = self.material("Flour")
        day = (timezone.localdate() - timedelta(days=5)).isoformat()
        res = self.buy(self.supplier(), [{"material": mat["id"], "quantity": "2", "unit_price": "100"}], invoice_date=day)
        self.assertEqual(res.status_code, 201, res.content)
        row = next(r for r in self.m.get("/api/inventory/reports/stock-summary/").json()["materials"] if r["id"] == mat["id"])
        self.assertEqual(row["last_bought"], day)

    def test_never_bought_has_no_last_bought_date(self):
        mat = self.material("Salt")
        row = next(r for r in self.m.get("/api/inventory/reports/stock-summary/").json()["materials"] if r["id"] == mat["id"])
        self.assertIsNone(row["last_bought"])
