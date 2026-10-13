from datetime import date

from psycopg2.errors import UniqueViolation

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestCommission(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Line = cls.env["drkds.commission.line"]
        cls.Rate = cls.env["drkds.commission.rate"]
        cls.company = cls.company_data["company"]
        groups = cls.env.ref("sales_team.group_sale_salesman") | cls.env.ref("account.group_account_invoice")
        cls.sales_a = cls.env["res.users"].create({
            "name": "Sales A", "login": "cml_sales_a", "group_ids": [Command.set(groups.ids)],
            "company_id": cls.company.id, "company_ids": [Command.set(cls.company.ids)],
            "drkds_commission_rate": 5.0,
        })
        cls.sales_b = cls.env["res.users"].create({
            "name": "Sales B", "login": "cml_sales_b", "group_ids": [Command.set(groups.ids)],
            "company_id": cls.company.id, "company_ids": [Command.set(cls.company.ids)],
            "drkds_commission_rate": 0.0,
        })
        cls.manager = cls.env["res.users"].create({
            "name": "Sales Manager", "login": "cml_manager",
            "group_ids": [Command.set((cls.env.ref("sales_team.group_sale_manager")
                                       | cls.env.ref("account.group_account_invoice")).ids)],
            "company_id": cls.company.id, "company_ids": [Command.set(cls.company.ids)],
        })
        # product_a sits in product_category (from the common setup); hardware is a child
        # of it with its own rate, and gadgets a grandchild inheriting the hardware rate.
        cls.categ_hardware = cls.env["product.category"].create({
            "name": "Hardware", "parent_id": cls.product_category.id,
        })
        cls.categ_gadgets = cls.env["product.category"].create({
            "name": "Gadgets", "parent_id": cls.categ_hardware.id,
        })
        cls.product_hw = cls._create_product(name="Router", categ_id=cls.categ_hardware.id, lst_price=3000.0)
        cls.product_gadget = cls._create_product(name="Dongle", categ_id=cls.categ_gadgets.id, lst_price=500.0)
        cls.Rate.create({"user_id": cls.sales_a.id, "categ_id": cls.categ_hardware.id, "rate": 10.0})

    def _invoice(self, user, lines, move_type="out_invoice", invoice_date=date(2026, 3, 10), post=True, **extra):
        """lines: (product, qty, price_unit)."""
        move = self.env["account.move"].create({
            "move_type": move_type,
            "partner_id": self.partner_a.id,
            "invoice_user_id": user.id,
            "invoice_date": invoice_date,
            "invoice_line_ids": [
                Command.create({
                    "product_id": p.id, "quantity": q, "price_unit": pu,
                    "tax_ids": [Command.clear()],
                }) for p, q, pu in lines
            ],
            **extra,
        })
        if post:
            move.action_post()
        return move

    # -- rates ---------------------------------------------------------------
    def test_rate_lookup(self):
        get = self.Rate._get_rate
        self.assertEqual(get(self.sales_a, self.product_category, self.company), 5.0, "default")
        self.assertEqual(get(self.sales_a, self.categ_hardware, self.company), 10.0, "override")
        self.assertEqual(get(self.sales_a, self.categ_gadgets, self.company), 10.0, "inherited from parent")
        self.assertEqual(get(self.sales_b, self.categ_hardware, self.company), 0.0, "no rate at all")
        self.assertEqual(get(self.env["res.users"], self.categ_hardware, self.company), 0.0)
        # The nearest ancestor wins over a further one.
        self.Rate.create({"user_id": self.sales_a.id, "categ_id": self.categ_gadgets.id, "rate": 2.5})
        self.assertEqual(get(self.sales_a, self.categ_gadgets, self.company), 2.5)
        self.assertEqual(get(self.sales_a, self.categ_hardware, self.company), 10.0)

    def test_rate_constraints(self):
        with self.assertRaises(ValidationError):
            self.Rate.create({"user_id": self.sales_a.id, "categ_id": self.categ_gadgets.id, "rate": 150.0})
        with self.assertRaises(ValidationError):
            self.Rate.create({"user_id": self.sales_a.id, "categ_id": self.categ_gadgets.id, "rate": -1.0})
        with mute_logger("odoo.sql_db"), self.assertRaises(UniqueViolation):
            self.Rate.create({"user_id": self.sales_a.id, "categ_id": self.categ_hardware.id, "rate": 7.0})

    # -- posting -------------------------------------------------------------
    def test_post_creates_lines(self):
        # product_a: 2 x 1000 = 2000 at 5% = 100; router: 1 x 3000 at 10% = 300
        inv = self._invoice(self.sales_a, [(self.product_a, 2, 1000.0), (self.product_hw, 1, 3000.0)])
        lines = inv.drkds_commission_line_ids
        self.assertEqual(len(lines), 2)
        by_product = {l.product_id: l for l in lines}
        self.assertEqual(by_product[self.product_a].base_amount, 2000.0)
        self.assertEqual(by_product[self.product_a].rate, 5.0)
        self.assertEqual(by_product[self.product_a].amount, 100.0)
        self.assertEqual(by_product[self.product_hw].base_amount, 3000.0)
        self.assertEqual(by_product[self.product_hw].rate, 10.0)
        self.assertEqual(by_product[self.product_hw].amount, 300.0)
        self.assertEqual(set(lines.mapped("user_id")), {self.sales_a})
        self.assertEqual(set(lines.mapped("date")), {date(2026, 3, 10)})
        self.assertEqual(set(lines.mapped("state")), {"unpaid"})
        self.assertEqual(set(lines.mapped("partner_id")), {self.partner_a})
        self.assertEqual(inv.drkds_commission_count, 2)

    def test_draft_invoice_has_no_lines(self):
        inv = self._invoice(self.sales_a, [(self.product_a, 1, 1000.0)], post=False)
        self.assertFalse(inv.drkds_commission_line_ids)

    def test_zero_rate_no_lines(self):
        inv = self._invoice(self.sales_b, [(self.product_a, 1, 1000.0), (self.product_hw, 1, 3000.0)])
        self.assertFalse(inv.drkds_commission_line_ids)
        # A category override of 0% switches commission off for that category only.
        self.Rate.create({"user_id": self.sales_a.id, "categ_id": self.categ_gadgets.id, "rate": 0.0})
        inv = self._invoice(self.sales_a, [(self.product_a, 1, 1000.0), (self.product_gadget, 4, 500.0)])
        self.assertEqual(inv.drkds_commission_line_ids.mapped("product_id"), self.product_a)
        self.assertEqual(inv.drkds_commission_line_ids.amount, 50.0)

    def test_discount_uses_subtotal(self):
        # 10 x 100 with 20% discount: subtotal 800, at 5% = 40
        inv = self.env["account.move"].create({
            "move_type": "out_invoice", "partner_id": self.partner_a.id,
            "invoice_user_id": self.sales_a.id, "invoice_date": date(2026, 3, 1),
            "invoice_line_ids": [Command.create({
                "product_id": self.product_a.id, "quantity": 10, "price_unit": 100.0,
                "discount": 20.0, "tax_ids": [Command.clear()],
            })],
        })
        inv.action_post()
        self.assertEqual(inv.drkds_commission_line_ids.base_amount, 800.0)
        self.assertEqual(inv.drkds_commission_line_ids.amount, 40.0)

    def test_sections_notes_and_vendor_bills_ignored(self):
        inv = self.env["account.move"].create({
            "move_type": "out_invoice", "partner_id": self.partner_a.id,
            "invoice_user_id": self.sales_a.id, "invoice_date": date(2026, 3, 1),
            "invoice_line_ids": [
                Command.create({"display_type": "line_section", "name": "Section"}),
                Command.create({"product_id": self.product_a.id, "quantity": 1, "price_unit": 100.0,
                                "tax_ids": [Command.clear()]}),
                Command.create({"display_type": "line_note", "name": "Note"}),
            ],
        })
        inv.action_post()
        self.assertEqual(len(inv.drkds_commission_line_ids), 1)
        bill = self._invoice(self.sales_a, [(self.product_a, 1, 1000.0)], move_type="in_invoice")
        self.assertFalse(bill.drkds_commission_line_ids)

    def test_foreign_currency_converted(self):
        # Rate 2.0 from 2017: 2 EUR = 1 company currency. 1000 EUR -> 500, at 5% = 25.
        other = self.setup_other_currency("EUR")
        inv = self._invoice(self.sales_a, [(self.product_a, 1, 1000.0)], currency_id=other.id)
        self.assertEqual(inv.drkds_commission_line_ids.currency_id, self.company.currency_id)
        self.assertEqual(inv.drkds_commission_line_ids.base_amount, 500.0)
        self.assertEqual(inv.drkds_commission_line_ids.amount, 25.0)

    # -- credit notes --------------------------------------------------------
    def test_credit_note_negative(self):
        inv = self._invoice(self.sales_a, [(self.product_a, 2, 1000.0)])
        reversal = self.env["account.move.reversal"].with_context(
            active_model="account.move", active_ids=inv.ids,
        ).create({"journal_id": inv.journal_id.id, "reason": "returned", "date": date(2026, 3, 15)})
        refund = self.env["account.move"].browse(reversal.refund_moves()["res_id"])
        self.assertEqual(refund.move_type, "out_refund")
        refund.action_post()
        self.assertEqual(refund.drkds_commission_line_ids.base_amount, -2000.0)
        self.assertEqual(refund.drkds_commission_line_ids.amount, -100.0)
        self.assertEqual(refund.drkds_commission_line_ids.user_id, self.sales_a)
        # The invoice's own line stays; the pair nets to zero.
        self.assertEqual(sum((inv + refund).drkds_commission_line_ids.mapped("amount")), 0.0)

    def test_direct_credit_note(self):
        refund = self._invoice(self.sales_a, [(self.product_hw, 1, 3000.0)], move_type="out_refund")
        self.assertEqual(refund.drkds_commission_line_ids.amount, -300.0)

    # -- lifecycle -----------------------------------------------------------
    def test_cancel_removes_and_repost_recomputes_once(self):
        inv = self._invoice(self.sales_a, [(self.product_a, 2, 1000.0), (self.product_hw, 1, 3000.0)])
        first_ids = inv.drkds_commission_line_ids.ids
        inv.button_draft()
        self.assertFalse(inv.drkds_commission_line_ids)
        self.assertFalse(self.Line.search([("id", "in", first_ids)]))
        inv.action_post()
        self.assertEqual(len(inv.drkds_commission_line_ids), 2)
        self.assertEqual(sum(inv.drkds_commission_line_ids.mapped("amount")), 400.0)
        # Changing the rate between posts is picked up by the recompute.
        inv.button_draft()
        self.sales_a.drkds_commission_rate = 8.0
        inv.action_post()
        self.assertEqual(sum(inv.drkds_commission_line_ids.mapped("amount")), 160.0 + 300.0)
        inv.button_cancel()
        self.assertEqual(inv.state, "cancel")
        self.assertFalse(inv.drkds_commission_line_ids)
        self.assertFalse(self.Line.search([("move_id", "=", inv.id)]))

    def test_regenerate_never_duplicates(self):
        inv = self._invoice(self.sales_a, [(self.product_a, 1, 1000.0)])
        self.Line._generate_for_moves(inv)
        self.Line._generate_for_moves(inv)
        self.assertEqual(len(inv.drkds_commission_line_ids), 1)
        self.assertEqual(inv.drkds_commission_line_ids.amount, 50.0)

    def test_unlink_invoice_cascades(self):
        inv = self._invoice(self.sales_a, [(self.product_a, 1, 1000.0)])
        line_ids = inv.drkds_commission_line_ids.ids
        inv.button_draft()
        inv.unlink()
        self.assertFalse(self.Line.search([("id", "in", line_ids)]))

    # -- paid ----------------------------------------------------------------
    def test_mark_paid(self):
        inv = self._invoice(self.sales_a, [(self.product_a, 1, 1000.0)])
        line = inv.drkds_commission_line_ids
        with self.assertRaises(UserError):
            line.with_user(self.sales_a).action_mark_paid()
        line.with_user(self.manager).action_mark_paid()
        self.assertEqual(line.state, "paid")
        self.assertEqual(line.paid_date, date.today())
        # Paid commission blocks a reset to draft and a delete...
        with self.assertRaises(UserError):
            inv.button_draft()
        with self.assertRaises(UserError):
            inv.button_cancel()
        with self.assertRaises(UserError):
            line.unlink()
        # ...and a regenerate leaves the paid line alone.
        self.Line._generate_for_moves(inv)
        self.assertEqual(inv.drkds_commission_line_ids, line)
        self.assertEqual(line.state, "paid")
        # Unpaid again: the reset goes through.
        line.with_user(self.manager).action_mark_unpaid()
        self.assertEqual(line.state, "unpaid")
        self.assertFalse(line.paid_date)
        inv.button_draft()
        self.assertFalse(inv.drkds_commission_line_ids)

    # -- security ------------------------------------------------------------
    def test_salesperson_sees_own_lines_only(self):
        self.sales_b.drkds_commission_rate = 4.0
        inv_a = self._invoice(self.sales_a, [(self.product_a, 1, 1000.0)])
        inv_b = self._invoice(self.sales_b, [(self.product_a, 1, 1000.0)])
        self.assertEqual(self.Line.with_user(self.sales_a).search([]), inv_a.drkds_commission_line_ids)
        self.assertEqual(self.Line.with_user(self.sales_b).search([]), inv_b.drkds_commission_line_ids)
        self.assertEqual(
            self.Line.with_user(self.manager).search([]),
            inv_a.drkds_commission_line_ids + inv_b.drkds_commission_line_ids,
        )
        with self.assertRaises(AccessError):
            inv_b.drkds_commission_line_ids.with_user(self.sales_a).read(["amount"])
        with self.assertRaises(AccessError):
            self.Rate.with_user(self.sales_a).create({
                "user_id": self.sales_a.id, "categ_id": self.categ_gadgets.id, "rate": 50.0,
            })
        with self.assertRaises(AccessError):
            inv_a.drkds_commission_line_ids.with_user(self.sales_a).write({"state": "paid"})
        # A salesperson may read their own rates, including from the user form.
        self.assertEqual(self.Rate.with_user(self.sales_a).search([]).mapped("rate"), [10.0])
        self.assertEqual(self.sales_a.with_user(self.sales_a).drkds_commission_rate, 5.0)

    def test_salesperson_posting_own_invoice(self):
        # Posting as the salesperson (billing rights, not manager) still writes the lines.
        inv = self._invoice(self.sales_a, [(self.product_a, 1, 1000.0)], post=False)
        inv.with_user(self.sales_a).action_post()
        self.assertEqual(inv.drkds_commission_line_ids.amount, 50.0)
