"""End-to-end: a monthly retainer of 25,000 plus 18% GST for three months.

Hand-computed: each invoice is 25,000 untaxed, 4,500 tax, 29,500 total.
Three invoices: 75,000 untaxed, 13,500 tax, 88,500 in all.
"""
from datetime import date

from freezegun import freeze_time

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import Form, tagged


@tagged("post_install", "-at_install")
class TestRecurringInvoiceScenario(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.gst_18 = cls.env["account.tax"].create({
            "name": "GST 18% (scenario)",
            "amount_type": "percent",
            "amount": 18.0,
            "type_tax_use": "sale",
            "company_id": cls.company_data["company"].id,
        })
        cls.retainer = cls.env["product.product"].create({
            "name": "Monthly Retainer",
            "type": "service",
            "list_price": 25000.0,
            "taxes_id": [Command.set(cls.gst_18.ids)],
            "property_account_income_id": cls.company_data["default_account_revenue"].id,
        })
        cls.client = cls.env["res.partner"].create({"name": "Sharma Textiles Pvt Ltd"})

    def test_monthly_retainer(self):
        # 1. The accountant fills the form the way the UI does.
        f = Form(self.env["drkds.recurring.invoice"])
        f.name = "Retainer - Sharma Textiles"
        f.partner_id = self.client
        f.interval_number = 1
        f.interval_unit = "month"
        f.next_date = date(2026, 1, 1)
        f.end_date = date(2026, 3, 1)
        f.auto_post = True
        with f.line_ids.new() as line:
            line.product_id = self.retainer  # pulls description, price and tax
        tpl = f.save()
        self.assertEqual(tpl.line_ids.price_unit, 25000.0)
        self.assertEqual(tpl.line_ids.tax_ids, self.gst_18)
        self.assertEqual(tpl.amount_untaxed, 25000.0)
        self.assertEqual(tpl.amount_tax, 4500.0)
        self.assertEqual(tpl.amount_total, 29500.0)
        self.assertEqual(tpl.state, "draft")
        tpl.action_start()

        # 2. January: the scheduler issues and posts the first invoice.
        with freeze_time("2026-01-01"):
            self.env["drkds.recurring.invoice"]._cron_generate_invoices()
        jan = tpl.invoice_ids
        self.assertEqual(len(jan), 1)
        self.assertEqual(jan.state, "posted")
        self.assertEqual(jan.invoice_date, date(2026, 1, 1))
        self.assertEqual(jan.amount_total, 29500.0)
        self.assertEqual(jan.amount_residual, 29500.0)
        self.assertEqual(jan.invoice_line_ids.product_id, self.retainer)
        self.assertEqual(tpl.next_date, date(2026, 2, 1))

        # 3. The client asks for a hold; the template is paused mid January.
        with freeze_time("2026-01-20"):
            tpl.action_pause()
        with freeze_time("2026-02-05"):
            self.assertFalse(self.env["drkds.recurring.invoice"]._cron_generate_invoices())
        self.assertEqual(tpl.invoice_count, 1)
        self.assertEqual(tpl.next_date, date(2026, 2, 1), "a pause keeps the schedule")

        # 4. Hold lifted: resume and issue February by hand with Generate Now.
        with freeze_time("2026-02-10"):
            tpl.action_start()
            action = tpl.action_generate_now()
        feb = self.env["account.move"].browse(action["res_id"])
        self.assertEqual(feb.recurring_id, tpl)
        self.assertEqual(feb.invoice_date, date(2026, 2, 1))
        self.assertEqual(feb.state, "posted")
        self.assertEqual(tpl.next_date, date(2026, 3, 1))
        # Pressing it again the same day must not duplicate; the date has moved on.
        with freeze_time("2026-02-10"):
            self.assertFalse(self.env["drkds.recurring.invoice"]._cron_generate_invoices())
        self.assertEqual(tpl.invoice_count, 2)

        # 5. March: last invoice of the contract, template closes itself.
        with freeze_time("2026-03-01"):
            self.env["drkds.recurring.invoice"]._cron_generate_invoices()
        self.assertEqual(tpl.invoice_count, 3)
        self.assertEqual(tpl.state, "done")
        self.assertEqual(tpl.last_invoice_date, date(2026, 3, 1))
        self.assertEqual(tpl.next_date, date(2026, 4, 1))

        # 6. Nothing in April, and the books carry the three invoices.
        with freeze_time("2026-04-01"):
            self.assertFalse(self.env["drkds.recurring.invoice"]._cron_generate_invoices())
        invoices = tpl.invoice_ids
        self.assertEqual(len(invoices), 3)
        self.assertEqual(sum(invoices.mapped("amount_untaxed")), 75000.0)
        self.assertEqual(sum(invoices.mapped("amount_tax")), 13500.0)
        self.assertEqual(sum(invoices.mapped("amount_total")), 88500.0)
        self.assertEqual(set(invoices.mapped("state")), {"posted"})
        self.assertEqual(
            sorted(invoices.mapped("invoice_date")),
            [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)],
        )
        # The smart button lists exactly these invoices.
        action = tpl.action_view_invoices()
        self.assertEqual(
            self.env["account.move"].search(action["domain"]), invoices,
        )
