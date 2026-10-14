from datetime import date

from lxml import etree
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
        # An invoicing clerk with no sales rights at all.
        cls.billing = cls.env["res.users"].create({
            "name": "Billing Clerk", "login": "cml_billing",
            "group_ids": [Command.set(cls.env.ref("account.group_account_invoice").ids)],
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

    def _invoice(self, user, lines, move_type="out_invoice", invoice_date=date(2026, 3, 10), post=True,
                 company=None, **extra):
        """lines: (product, qty, price_unit)."""
        move = self.env["account.move"].with_company(company or self.company).create({
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

    def _refund(self, invoice, refund_date=date(2026, 3, 15)):
        """A draft credit note made from ``invoice`` with the Credit Note wizard."""
        reversal = self.env["account.move.reversal"].with_context(
            active_model="account.move", active_ids=invoice.ids,
        ).create({"journal_id": invoice.journal_id.id, "reason": "returned", "date": refund_date})
        return self.env["account.move"].browse(reversal.refund_moves()["res_id"])

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

    def test_branch_uses_parent_company_rates(self):
        self.company.write({"child_ids": [Command.create({"name": "Pune Branch"})]})
        self.cr.precommit.run()  # loads the branch's chart, as the UI does on save
        branch = self.company.child_ids
        self.sales_a.company_ids = [Command.link(branch.id)]
        # The 10% Hardware rate is set on the parent company and covers its branch:
        # 1 x 3000 at 10% = 300, not the 5% default (150).
        inv = self._invoice(self.sales_a, [(self.product_hw, 1, 3000.0)], company=branch)
        self.assertEqual(inv.company_id, branch)
        self.assertEqual(inv.drkds_commission_line_ids.company_id, branch)
        self.assertEqual(inv.drkds_commission_line_ids.rate, 10.0)
        self.assertEqual(inv.drkds_commission_line_ids.amount, 300.0)
        # A rate on the branch itself wins there, and only there.
        self.Rate.create({"user_id": self.sales_a.id, "categ_id": self.categ_hardware.id,
                          "rate": 6.0, "company_id": branch.id})
        get = self.Rate._get_rate
        self.assertEqual(get(self.sales_a, self.categ_hardware, branch), 6.0)
        self.assertEqual(get(self.sales_a, self.categ_hardware, self.company), 10.0)
        # The nearer category still beats the nearer company.
        self.Rate.create({"user_id": self.sales_a.id, "categ_id": self.categ_gadgets.id, "rate": 2.5})
        self.assertEqual(get(self.sales_a, self.categ_gadgets, branch), 2.5)

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
        self.assertEqual(inv.drkds_commission_line_count, 2)

    def test_smart_button_counts_this_modules_lines(self):
        # The invoice's Commission button reads its figure from a field of this
        # module alone. A field name shared with another commission app on
        # account.move is redefined by whichever loads last, and the button then
        # shows the other app's count (0 here) and hides itself.
        inv = self._invoice(self.sales_a, [(self.product_a, 2, 1000.0), (self.product_hw, 1, 3000.0)])
        arch = self.env["account.move"].get_views([(False, "form")])["views"]["form"]["arch"]
        fields = etree.fromstring(arch).xpath("//button[@name='action_view_drkds_commission_lines']//field")
        self.assertEqual(len(fields), 1)
        fname = fields[0].get("name")
        self.assertEqual(self.env["ir.model.fields"]._get("account.move", fname).modules, "drkds_commission_lite")
        self.assertEqual(inv[fname], len(inv.drkds_commission_line_ids))
        self.assertEqual(inv[fname], 2)

    def test_rates_are_not_totalled_in_groups(self):
        # Grouped lists and the pivot used to add percentages up (three lines at
        # 3% showed 9.00 on the salesperson's row). Amounts still add up.
        self._invoice(self.sales_a, [(self.product_a, 1, 1000.0), (self.product_hw, 1, 3000.0)])
        for model in ("drkds.commission.line", "drkds.commission.rate"):
            self.assertIsNone(self.env[model].fields_get(["rate"])["rate"].get("aggregator"), model)
        groups = self.Line.formatted_read_group(
            [("user_id", "=", self.sales_a.id)], ["user_id"], ["amount:sum", "base_amount:sum"])
        self.assertEqual(groups[0]["amount:sum"], 350.0)
        self.assertEqual(groups[0]["base_amount:sum"], 4000.0)

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

    def test_foreign_currency_uses_the_booked_rate(self):
        # The table says 2 EUR per unit, but the invoice is booked at a rate typed in by
        # hand, 2.5: 1000 EUR is 400 in the books, at 5% = 20 (not 500 -> 25).
        other = self.setup_other_currency("EUR")
        inv = self._invoice(self.sales_a, [(self.product_a, 1, 1000.0)], currency_id=other.id, post=False)
        inv.invoice_currency_rate = 2.5
        inv.action_post()
        self.assertEqual(inv.invoice_line_ids.balance, -400.0)
        self.assertEqual(inv.drkds_commission_line_ids.base_amount, 400.0)
        self.assertEqual(inv.drkds_commission_line_ids.amount, 20.0)

    def test_foreign_currency_credit_note_after_the_rate_moved(self):
        # Invoiced in March at 2.0: 1000 EUR -> 500 -> 25. By April the table says 4.0, but
        # a credit note keeps its invoice's rate and books -500, so it must take back 25,
        # not 12.50 (which would leave 12.50 of commission on a fully refunded sale).
        other = self.setup_other_currency("EUR")
        self.env["res.currency.rate"].create({
            "currency_id": other.id, "name": date(2026, 4, 1), "rate": 4.0, "company_id": self.company.id,
        })
        inv = self._invoice(self.sales_a, [(self.product_a, 1, 1000.0)], currency_id=other.id)
        refund = self._refund(inv, refund_date=date(2026, 4, 15))
        refund.action_post()
        self.assertEqual(refund.invoice_line_ids.balance, 500.0)
        self.assertEqual(refund.drkds_commission_line_ids.base_amount, -500.0)
        self.assertEqual(refund.drkds_commission_line_ids.amount, -25.0)
        self.assertEqual(sum((inv + refund).drkds_commission_line_ids.mapped("amount")), 0.0)

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

    def test_credit_note_takes_back_the_rate_earned(self):
        # 2 x 1000 earned 5% = 100. The default then rises to 8%.
        inv = self._invoice(self.sales_a, [(self.product_a, 2, 1000.0)])
        self.sales_a.drkds_commission_rate = 8.0
        refund = self._refund(inv)
        refund.action_post()
        # -2000 at the 5% earned = -100, not -160 at today's 8%.
        self.assertEqual(refund.drkds_commission_line_ids.rate, 5.0)
        self.assertEqual(refund.drkds_commission_line_ids.amount, -100.0)
        self.assertEqual(sum((inv + refund).drkds_commission_line_ids.mapped("amount")), 0.0)

    def test_partial_credit_note_at_the_rate_earned(self):
        # 3 routers x 3000 = 9000 earned 10% = 900. The Hardware rate is then cut to 4%
        # and one router comes back: -3000 at 10% = -300, leaving 600.
        inv = self._invoice(self.sales_a, [(self.product_hw, 3, 3000.0)])
        self.Rate.search([("categ_id", "=", self.categ_hardware.id)]).rate = 4.0
        refund = self._refund(inv)
        refund.invoice_line_ids.quantity = 1
        refund.action_post()
        self.assertEqual(refund.drkds_commission_line_ids.base_amount, -3000.0)
        self.assertEqual(refund.drkds_commission_line_ids.rate, 10.0)
        self.assertEqual(refund.drkds_commission_line_ids.amount, -300.0)
        self.assertEqual(sum((inv + refund).drkds_commission_line_ids.mapped("amount")), 600.0)

    def test_credit_note_for_an_invoice_that_earned_nothing(self):
        # Sales B had no rate when this invoice was posted, so it earned nothing...
        inv = self._invoice(self.sales_b, [(self.product_a, 1, 1000.0)])
        self.assertFalse(inv.drkds_commission_line_ids)
        # ...and its credit note must not take anything back once B has a rate.
        self.sales_b.drkds_commission_rate = 4.0
        refund = self._refund(inv)
        # A product that was never on the invoice earned nothing either.
        refund.write({"invoice_line_ids": [Command.create({
            "product_id": self.product_hw.id, "quantity": 1, "price_unit": 3000.0, "tax_ids": [Command.clear()],
        })]})
        refund.action_post()
        self.assertFalse(refund.drkds_commission_line_ids)

    def test_credit_note_charged_to_who_earned_it(self):
        inv = self._invoice(self.sales_a, [(self.product_a, 1, 1000.0)])
        refund = self._refund(inv)
        refund.invoice_user_id = self.sales_b
        refund.action_post()
        self.assertEqual(refund.drkds_commission_line_ids.user_id, self.sales_a)
        self.assertEqual(refund.drkds_commission_line_ids.amount, -50.0)

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

    def test_salesperson_changed_after_posting(self):
        self.sales_b.drkds_commission_rate = 3.0
        inv = self._invoice(self.sales_a, [(self.product_a, 1, 1000.0)])
        self.assertEqual(inv.drkds_commission_line_ids.amount, 50.0)
        # Corrected to B on the posted invoice: A's 50 goes, B earns 3% = 30.
        inv.invoice_user_id = self.sales_b
        self.assertEqual(inv.drkds_commission_line_ids.user_id, self.sales_b)
        self.assertEqual(inv.drkds_commission_line_ids.amount, 30.0)
        # B's 30 is paid, then the invoice goes back to A: B owes the 30, A earns 50.
        inv.drkds_commission_line_ids.with_user(self.manager).action_mark_paid()
        inv.invoice_user_id = self.sales_a
        lines = inv.drkds_commission_line_ids
        b_lines = lines.filtered(lambda l: l.user_id == self.sales_b)
        self.assertEqual(sorted(b_lines.mapped("amount")), [-30.0, 30.0])
        self.assertEqual(b_lines.filtered(lambda l: l.state == "unpaid").amount, -30.0)
        self.assertEqual(lines.filtered(lambda l: l.user_id == self.sales_a).amount, 50.0)

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
        # A second click changes nothing, a paid line cannot be deleted, and a
        # regenerate of the unchanged invoice writes nothing new.
        line.with_user(self.manager).action_mark_paid()
        self.assertEqual(line.paid_date, date.today())
        with self.assertRaises(UserError):
            line.unlink()
        self.Line._generate_for_moves(inv)
        self.assertEqual(inv.drkds_commission_line_ids, line)
        # Unpaid again (a mistaken click): the line is back to an ordinary unpaid line.
        line.with_user(self.manager).action_mark_unpaid()
        self.assertEqual(line.state, "unpaid")
        self.assertFalse(line.paid_date)
        inv.button_draft()
        self.assertFalse(inv.drkds_commission_line_ids)

    def test_reset_and_cancel_after_paid(self):
        # 1 x 1000 at 5% = 50, paid out.
        inv = self._invoice(self.sales_a, [(self.product_a, 1, 1000.0)])
        paid = inv.drkds_commission_line_ids
        paid.with_user(self.manager).action_mark_paid()
        # A billing clerk without sales rights resets it: core accounting is not blocked.
        inv.with_user(self.billing).button_draft()
        self.assertEqual(inv.state, "draft")
        self.assertEqual(paid.state, "paid")
        self.assertEqual(paid.amount, 50.0)
        take_back = inv.drkds_commission_line_ids - paid
        self.assertEqual(take_back.amount, -50.0)
        self.assertEqual(take_back.base_amount, -1000.0)
        self.assertEqual(take_back.state, "unpaid")
        self.assertEqual(take_back.user_id, self.sales_a)
        # Editing the draft (the paid line's invoice line is replaced) keeps the paid record.
        inv.write({"invoice_line_ids": [
            Command.delete(inv.invoice_line_ids.id),
            Command.create({"product_id": self.product_a.id, "quantity": 1, "price_unit": 1000.0,
                            "tax_ids": [Command.clear()]}),
        ]})
        self.assertTrue(paid.exists())
        self.assertFalse(paid.move_line_id)
        # Posted again at 8%: 80 earned, 50 already paid, 30 still owed.
        self.sales_a.drkds_commission_rate = 8.0
        inv.with_user(self.billing).action_post()
        lines = inv.drkds_commission_line_ids
        self.assertEqual(sum(lines.mapped("amount")), 80.0)
        self.assertEqual(sum(lines.filtered(lambda l: l.state == "unpaid").mapped("amount")), 30.0)
        # Cancelled: nothing is earned, and the 50 paid is owed back.
        inv.with_user(self.billing).button_cancel()
        self.assertEqual(inv.state, "cancel")
        lines = inv.drkds_commission_line_ids
        self.assertEqual(sum(lines.mapped("amount")), 0.0)
        owed = lines.filtered(lambda l: l.state == "unpaid")
        self.assertEqual(owed.amount, -50.0)
        # Once the take-back is settled too, another reset adds nothing.
        owed.with_user(self.manager).action_mark_paid()
        inv.button_draft()
        self.assertEqual(inv.drkds_commission_line_ids, paid + owed)
        # The invoice now carries a record of money paid out: it cannot be deleted.
        with self.assertRaisesRegex(UserError, "Commission has already been paid out"):
            inv.unlink()

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

    def test_managers_cannot_edit_lines_directly(self):
        # The manager is also a salesperson here, settling their own commission.
        self.manager.drkds_commission_rate = 5.0
        inv = self._invoice(self.manager, [(self.product_a, 1, 1000.0)])
        line = inv.drkds_commission_line_ids
        for vals in ({"amount": 99999.0}, {"rate": 50.0}, {"state": "paid"}, {"user_id": self.sales_a.id}):
            with self.assertRaises(AccessError):
                line.with_user(self.manager).write(vals)
        self.assertEqual(line.amount, 50.0)
        # The buttons still work, and stamp the date.
        line.with_user(self.manager).action_mark_paid()
        self.assertEqual(line.state, "paid")
        self.assertEqual(line.paid_date, date.today())
        line.with_user(self.manager).action_mark_unpaid()
        self.assertEqual(line.state, "unpaid")

    def test_rates_hidden_from_colleagues(self):
        employee = self.env["res.users"].create({
            "name": "Clerk", "login": "cml_clerk",
            "group_ids": [Command.set(self.env.ref("base.group_user").ids)],
            "company_id": self.company.id, "company_ids": [Command.set(self.company.ids)],
        })
        for user in (employee, self.sales_b, self.billing):
            with self.assertRaises(AccessError):
                self.sales_a.with_user(user).read(["drkds_commission_rate"])
        # Your own rate stays readable, and managers see everyone's.
        self.assertEqual(self.sales_a.with_user(self.sales_a).read(["drkds_commission_rate"])[0]["drkds_commission_rate"], 5.0)
        self.assertEqual(self.sales_a.with_user(self.manager).read(["drkds_commission_rate"])[0]["drkds_commission_rate"], 5.0)

    def test_invoice_fields_only_for_users_who_can_read_commission(self):
        auditor = self.env["res.users"].create({
            "name": "Auditor", "login": "cml_auditor",
            "group_ids": [Command.set(self.env.ref("account.group_account_readonly").ids)],
            "company_id": self.company.id, "company_ids": [Command.set(self.company.ids)],
        })
        inv = self._invoice(self.sales_a, [(self.product_a, 1, 1000.0)])
        # A read-only accountant has no access to commission lines: the fields are not
        # offered to them (export, custom views), so nothing can trip an AccessError.
        self.assertNotIn("drkds_commission_line_count", self.env["account.move"].with_user(auditor).fields_get())
        self.assertNotIn("drkds_commission_line_ids", self.env["account.move"].with_user(auditor).fields_get())
        self.assertTrue(inv.with_user(auditor).read(["name", "amount_untaxed"]))
        # The billing clerk keeps the smart button.
        self.env.invalidate_all()
        self.assertEqual(inv.with_user(self.billing).read(["drkds_commission_line_count"])[0]["drkds_commission_line_count"], 1)

    def test_salesperson_posting_own_invoice(self):
        # Posting as the salesperson (billing rights, not manager) still writes the lines.
        inv = self._invoice(self.sales_a, [(self.product_a, 1, 1000.0)], post=False)
        inv.with_user(self.sales_a).action_post()
        self.assertEqual(inv.drkds_commission_line_ids.amount, 50.0)
