"""End-to-end: two salespeople over two months, three invoices and one refund.

Rates
    Asha: default 5%.
    Ravi: default 3%, 10% on the Services category.
Products
    Widget (Goods) 1,200 each; Consulting Day (Services) 8,000 each.

Hand-computed
    10 Jan  Asha  INV 1: 10 Widget = 12,000 @5% = 600; 1 Consulting = 8,000 @5% = 400   -> 1,000
    25 Jan  Ravi  INV 2:  5 Widget =  6,000 @3% = 180; 2 Consulting = 16,000 @10% = 1,600 -> 1,780
     5 Feb  Asha  INV 3:  3 Consulting = 24,000 @5% = 1,200                              -> 1,200
    20 Feb  Asha  refund of INV 1, 2 Widget = -2,400 @5% = -120                          ->  -120

    Asha: Jan 1,000, Feb 1,080, total 2,080.  Ravi: Jan 1,780, total 1,780.  All: 3,860.
    After paying January: paid 2,780, unpaid 1,080 (both Asha, February).
"""
from datetime import date

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestCommissionScenario(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.company_data["company"]
        groups = cls.env.ref("sales_team.group_sale_salesman") | cls.env.ref("account.group_account_invoice")
        cls.asha = cls.env["res.users"].create({
            "name": "Asha Verma", "login": "cml_asha", "group_ids": [Command.set(groups.ids)],
            "company_id": company.id, "company_ids": [Command.set(company.ids)],
            "drkds_commission_rate": 5.0,
        })
        cls.ravi = cls.env["res.users"].create({
            "name": "Ravi Iyer", "login": "cml_ravi", "group_ids": [Command.set(groups.ids)],
            "company_id": company.id, "company_ids": [Command.set(company.ids)],
            "drkds_commission_rate": 3.0,
        })
        cls.manager = cls.env["res.users"].create({
            "name": "Meera Nair", "login": "cml_meera",
            "group_ids": [Command.set(cls.env.ref("sales_team.group_sale_manager").ids)],
            "company_id": company.id, "company_ids": [Command.set(company.ids)],
        })
        cls.categ_goods = cls.env["product.category"].create({"name": "Goods", "parent_id": cls.product_category.id})
        cls.categ_services = cls.env["product.category"].create({"name": "Services", "parent_id": cls.product_category.id})
        cls.widget = cls._create_product(name="Widget", categ_id=cls.categ_goods.id, lst_price=1200.0)
        cls.consulting = cls._create_product(name="Consulting Day", categ_id=cls.categ_services.id,
                                             type="service", lst_price=8000.0)
        cls.env["drkds.commission.rate"].create({
            "user_id": cls.ravi.id, "categ_id": cls.categ_services.id, "rate": 10.0,
        })
        cls.customer = cls.env["res.partner"].create({"name": "Patel Traders"})

    def _invoice(self, user, invoice_date, lines):
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.customer.id,
            "invoice_user_id": user.id,
            "invoice_date": invoice_date,
            "invoice_line_ids": [
                Command.create({"product_id": p.id, "quantity": q, "price_unit": p.lst_price})
                for p, q in lines
            ],
        })
        move.action_post()
        return move

    def _totals(self, lines):
        """{(user, (year, month)): amount}"""
        out = {}
        for line in lines:
            key = (line.user_id, (line.date.year, line.date.month))
            out[key] = out.get(key, 0.0) + line.amount
        return out

    def test_two_months_two_salespeople(self):
        inv1 = self._invoice(self.asha, date(2026, 1, 10), [(self.widget, 10), (self.consulting, 1)])
        inv2 = self._invoice(self.ravi, date(2026, 1, 25), [(self.widget, 5), (self.consulting, 2)])
        inv3 = self._invoice(self.asha, date(2026, 2, 5), [(self.consulting, 3)])

        self.assertEqual(sorted(inv1.drkds_commission_line_ids.mapped("amount")), [400.0, 600.0])
        self.assertEqual(sorted(inv2.drkds_commission_line_ids.mapped("amount")), [180.0, 1600.0])
        self.assertEqual(inv2.drkds_commission_line_ids.filtered(
            lambda l: l.product_id == self.consulting).rate, 10.0)
        self.assertEqual(inv3.drkds_commission_line_ids.amount, 1200.0)

        # The customer returns two widgets from the January invoice.
        reversal = self.env["account.move.reversal"].with_context(
            active_model="account.move", active_ids=inv1.ids,
        ).create({"journal_id": inv1.journal_id.id, "reason": "2 widgets returned", "date": date(2026, 2, 20)})
        refund = self.env["account.move"].browse(reversal.refund_moves()["res_id"])
        refund.write({"invoice_line_ids": [
            Command.delete(refund.invoice_line_ids.filtered(lambda l: l.product_id == self.consulting).id),
        ]})
        refund.invoice_line_ids.filtered(lambda l: l.product_id == self.widget).quantity = 2
        self.assertEqual(refund.amount_untaxed, 2400.0)
        refund.action_post()
        self.assertEqual(refund.drkds_commission_line_ids.amount, -120.0)

        # Monthly totals by salesperson, as the pivot would show them.
        all_lines = self.env["drkds.commission.line"].with_user(self.manager).search([
            ("user_id", "in", (self.asha | self.ravi).ids),
        ])
        self.assertEqual(len(all_lines), 6)
        totals = self._totals(all_lines)
        self.assertEqual(totals[(self.asha, (2026, 1))], 1000.0)
        self.assertEqual(totals[(self.asha, (2026, 2))], 1080.0)
        self.assertEqual(totals[(self.ravi, (2026, 1))], 1780.0)
        self.assertNotIn((self.ravi, (2026, 2)), totals)
        self.assertEqual(sum(all_lines.filtered(lambda l: l.user_id == self.asha).mapped("amount")), 2080.0)
        self.assertEqual(sum(all_lines.filtered(lambda l: l.user_id == self.ravi).mapped("amount")), 1780.0)
        self.assertEqual(sum(all_lines.mapped("amount")), 3860.0)

        # The same figures through the ORM grouping the pivot relies on.
        grouped = self.env["drkds.commission.line"].with_user(self.manager)._read_group(
            [("user_id", "in", (self.asha | self.ravi).ids)],
            ["user_id", "date:month"], ["amount:sum"],
        )
        by_key = {(u, d.strftime("%Y-%m")): total for u, d, total in grouped}
        self.assertEqual(by_key, {
            (self.asha, "2026-01"): 1000.0,
            (self.asha, "2026-02"): 1080.0,
            (self.ravi, "2026-01"): 1780.0,
        })

        # Each salesperson sees only their own figures.
        self.assertEqual(sum(self.env["drkds.commission.line"].with_user(self.asha).search([]).mapped("amount")), 2080.0)
        self.assertEqual(sum(self.env["drkds.commission.line"].with_user(self.ravi).search([]).mapped("amount")), 1780.0)

        # Month end: the manager pays January.
        january = all_lines.filtered(lambda l: l.date.month == 1)
        january.with_user(self.manager).action_mark_paid()
        self.assertEqual(set(january.mapped("state")), {"paid"})
        self.assertEqual(sum(all_lines.filtered(lambda l: l.state == "paid").mapped("amount")), 2780.0)
        unpaid = all_lines.filtered(lambda l: l.state == "unpaid")
        self.assertEqual(sum(unpaid.mapped("amount")), 1080.0)
        self.assertEqual(set(unpaid.mapped("user_id")), {self.asha})
