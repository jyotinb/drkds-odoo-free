from datetime import date

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import new_test_user, tagged
from odoo.tools.misc import format_date

from .common import StatementCase


@tagged("post_install", "-at_install")
class TestStatement(StatementCase):
    """Running balance, as-at ageing and multi-currency, with hand-computed figures."""

    def test_activity_running_balance(self):
        """Opening 1,000 (INV1 before 1 March), then each movement in order."""
        data = self.customer._drkds_statement_data(
            date(2024, 3, 1), date(2024, 6, 30), "activity",
        )
        self.assertAlmostEqual(data["opening_balance"], 1000.0, 2)
        expected = [
            # date, debit, credit, running balance
            (date(2024, 3, 5), 0.0, 1000.0, 0.0),        # PAY1
            (date(2024, 4, 5), 800.0, 0.0, 800.0),       # INV2
            (date(2024, 4, 20), 0.0, 300.0, 500.0),      # PAY2
            (date(2024, 5, 15), 650.0, 0.0, 1150.0),     # INV3
            (date(2024, 6, 10), 420.0, 0.0, 1570.0),     # INV4
            (date(2024, 6, 25), 150.0, 0.0, 1720.0),     # INV5, 300 EUR
        ]
        self.assertEqual(len(data["lines"]), len(expected))
        for row, (d, debit, credit, balance) in zip(data["lines"], expected):
            self.assertEqual(row["date"], d)
            self.assertAlmostEqual(row["debit"], debit, 2)
            self.assertAlmostEqual(row["credit"], credit, 2)
            self.assertAlmostEqual(row["balance"], balance, 2)
        self.assertAlmostEqual(data["closing_balance"], 1720.0, 2)
        self.assertAlmostEqual(data["total_debit"], 2020.0, 2)
        self.assertAlmostEqual(data["total_credit"], 1300.0, 2)
        self.assertEqual(data["lines"][1]["document"], self.inv2.name)
        self.assertEqual(data["lines"][1]["due_date"], date(2024, 4, 5))

    def test_multi_currency_row_in_company_currency(self):
        """The EUR invoice is a 150.00 debit; the 300 EUR original is noted."""
        data = self.customer._drkds_statement_data(
            date(2024, 6, 1), date(2024, 6, 30), "activity",
        )
        row = data["lines"][-1]
        self.assertEqual(row["document"], self.inv5.name)
        self.assertAlmostEqual(row["debit"], 150.0, 2)
        self.assertEqual(row["currency"], self.eur)
        self.assertAlmostEqual(row["amount_currency"], 300.0, 2)
        # Company-currency rows carry no original-currency note.
        self.assertFalse(data["lines"][0]["currency"])

    def test_ageing_buckets_at_month_end(self):
        """As at 30 June 2024: 420 + 150 in 0-30, 650 in 31-60, 500 in 61-90."""
        ageing = self.customer._drkds_statement_ageing(date(2024, 6, 30))
        self.assertAlmostEqual(ageing["b0_30"], 570.0, 2)
        self.assertAlmostEqual(ageing["b31_60"], 650.0, 2)
        self.assertAlmostEqual(ageing["b61_90"], 500.0, 2)
        self.assertAlmostEqual(ageing["b90_plus"], 0.0, 2)
        self.assertAlmostEqual(ageing["total"], 1720.0, 2)

    def test_ageing_is_as_at_the_date(self):
        """Reprinting for an earlier date replays only the reconciliations made by then."""
        # 10 April: INV1 paid, INV2 fully open (5 days old), nothing else yet.
        ageing = self.customer._drkds_statement_ageing(date(2024, 4, 10))
        self.assertAlmostEqual(ageing["b0_30"], 800.0, 2)
        self.assertAlmostEqual(ageing["total"], 800.0, 2)
        # 30 April: PAY2 has reduced INV2 to 500, still 0-30 (25 days).
        ageing = self.customer._drkds_statement_ageing(date(2024, 4, 30))
        self.assertAlmostEqual(ageing["b0_30"], 500.0, 2)
        self.assertAlmostEqual(ageing["total"], 500.0, 2)
        # 4 March: INV1 open and 13 days old, PAY1 not yet made.
        ageing = self.customer._drkds_statement_ageing(date(2024, 3, 4))
        self.assertAlmostEqual(ageing["b0_30"], 1000.0, 2)
        # 31 August: INV2 (148 days) and INV3 (108 days) are over 90;
        # INV4 (82 days) and INV5 (67 days) sit in 61-90.
        ageing = self.customer._drkds_statement_ageing(date(2024, 8, 31))
        self.assertAlmostEqual(ageing["b90_plus"], 1150.0, 2)
        self.assertAlmostEqual(ageing["b61_90"], 570.0, 2)
        self.assertAlmostEqual(ageing["b31_60"], 0.0, 2)
        self.assertAlmostEqual(ageing["b0_30"], 0.0, 2)
        self.assertAlmostEqual(ageing["total"], 1720.0, 2)

    def test_outstanding_statement(self):
        """Outstanding only: open items at their open amount, no opening line."""
        data = self.customer._drkds_statement_data(
            date(2024, 1, 1), date(2024, 6, 30), "outstanding",
        )
        self.assertAlmostEqual(data["opening_balance"], 0.0, 2)
        docs = [(row["document"], row["debit"], row["balance"]) for row in data["lines"]]
        self.assertEqual(docs, [
            (self.inv2.name, 500.0, 500.0),
            (self.inv3.name, 650.0, 1150.0),
            (self.inv4.name, 420.0, 1570.0),
            (self.inv5.name, 150.0, 1720.0),
        ])
        self.assertAlmostEqual(data["closing_balance"], 1720.0, 2)

    def test_vendor_side(self):
        """A vendor bill reduces the net statement only when the vendor side is included."""
        self._invoice("2024-05-01", 200.0, move_type="in_invoice", ref="BILL-7")
        customer_only = self.customer._drkds_statement_data(
            date(2024, 3, 1), date(2024, 6, 30), "activity",
        )
        self.assertAlmostEqual(customer_only["closing_balance"], 1720.0, 2)
        both = self.customer._drkds_statement_data(
            date(2024, 3, 1), date(2024, 6, 30), "activity", include_vendor=True,
        )
        self.assertAlmostEqual(both["closing_balance"], 1520.0, 2)
        bill_row = next(r for r in both["lines"] if r["reference"] == "BILL-7")
        self.assertAlmostEqual(bill_row["credit"], 200.0, 2)
        ageing = both["ageing"]
        self.assertAlmostEqual(ageing["b31_60"], 450.0, 2)   # 650 - 200, bill is 60 days old
        self.assertAlmostEqual(ageing["total"], 1520.0, 2)

    def test_contact_rolls_up_to_company(self):
        """An invoice on a contact person appears on the company's statement."""
        contact = self.env["res.partner"].create({
            "name": "Asha at Meridian", "parent_id": self.customer.id,
        })
        self._invoice("2024-06-28", 75.0, partner=contact)
        data = self.customer._drkds_statement_data(
            date(2024, 6, 1), date(2024, 6, 30), "activity",
        )
        self.assertAlmostEqual(data["closing_balance"], 1795.0, 2)
        # And the contact's own figures are the company's.
        self.assertAlmostEqual(
            contact._drkds_statement_ageing(date(2024, 6, 30))["total"], 1795.0, 2,
        )

    def test_partner_ageing_fields_today(self):
        """Everything is well over 90 days old by now; the fields say so."""
        self.assertGreater((fields.Date.context_today(self.customer) - date(2024, 6, 25)).days, 90)
        self.assertAlmostEqual(self.customer.drkds_stmt_90_plus, 1720.0, 2)
        self.assertAlmostEqual(self.customer.drkds_stmt_0_30, 0.0, 2)
        self.assertAlmostEqual(self.customer.drkds_stmt_total_due, 1720.0, 2)
        self.assertEqual(self.customer.drkds_stmt_currency_id, self.company_data["currency"])
        stranger = self.env["res.partner"].create({"name": "Nobody Yet"})
        self.assertAlmostEqual(stranger.drkds_stmt_total_due, 0.0, 2)

    def test_draft_excluded(self):
        """Draft invoices never reach the statement."""
        self._create_invoice(
            invoice_date="2024-06-29", partner_id=self.customer.id,
            invoice_line_ids=[(0, 0, {"name": "draft", "quantity": 1, "price_unit": 999.0})],
        )
        data = self.customer._drkds_statement_data(
            date(2024, 6, 1), date(2024, 6, 30), "activity",
        )
        self.assertAlmostEqual(data["closing_balance"], 1720.0, 2)

    def test_other_company_excluded(self):
        """A posting in another company stays on that company's statement only."""
        company_2 = self.setup_other_company(name="Coastal Statement Co")["company"]
        self._invoice("2024-06-14", 333.0, company=company_2)
        data = self.customer._drkds_statement_data(date(2024, 6, 1), date(2024, 6, 30))
        self.assertAlmostEqual(data["closing_balance"], 1720.0, 2)
        self.assertAlmostEqual(data["ageing"]["total"], 1720.0, 2)
        other = self.customer._drkds_statement_data(
            date(2024, 6, 1), date(2024, 6, 30), company=company_2,
        )
        self.assertAlmostEqual(other["opening_balance"], 0.0, 2)
        self.assertAlmostEqual(other["closing_balance"], 333.0, 2)
        self.assertEqual(other["currency"], company_2.currency_id)

    def test_branch_postings_on_parent_statement(self):
        """A branch is the same legal entity: its invoices belong on the parent's statement.

        Core's partner ``credit`` counts them too. The branch's own statement
        still shows only what the branch posted.
        """
        branch = self.env["res.company"].create({
            "name": "Gujarat Branch", "parent_id": self.env.company.id,
        })
        self.env.cr.precommit.run()  # loads the branch's chart, as core's tests do
        self._invoice("2024-06-20", 230.0, company=branch)
        parent = self.customer._drkds_statement_data(date(2024, 6, 1), date(2024, 6, 30))
        self.assertAlmostEqual(parent["closing_balance"], 1950.0, 2)   # 1,720 + 230
        self.assertAlmostEqual(parent["ageing"]["b0_30"], 800.0, 2)     # 570 + 230
        self.assertAlmostEqual(parent["ageing"]["total"], 1950.0, 2)
        own = self.customer._drkds_statement_data(
            date(2024, 6, 1), date(2024, 6, 30), company=branch,
        )
        self.assertAlmostEqual(own["closing_balance"], 230.0, 2)

    def test_outstanding_open_amount_in_original_currency(self):
        """Part-paid in EUR after the rate moved: the open amount, not the invoice total.

        INV5 is 300 EUR at 2.0 = 150.00. On 5 July 2024, at 2.5, the customer
        pays 100 EUR = 40.00; Odoo books a 10.00 exchange difference (100 EUR
        was 50.00 at the invoice rate). As at 31 July, 200 EUR = 100.00 is open.
        """
        self.env["res.currency.rate"].create({
            "name": "2024-07-01", "rate": 2.5, "currency_id": self.eur.id,
            "company_id": self.env.company.id,
        })
        payment = self._pay(self.inv5, "2024-07-05", 100.0)
        exchange = self.inv5.line_ids.matched_credit_ids.exchange_move_id
        self.assertEqual(len(exchange), 1)
        self.assertLessEqual(exchange.date, date(2024, 7, 31))

        data = self.customer._drkds_statement_data(
            date(2024, 7, 1), date(2024, 7, 31), "outstanding",
        )
        row = next(r for r in data["lines"] if r["document"] == self.inv5.name)
        self.assertAlmostEqual(row["debit"], 100.0, 2)
        self.assertEqual(row["currency"], self.eur)
        self.assertAlmostEqual(row["amount_currency"], 200.0, 2)

        # Activity: the payment shows its EUR amount; the exchange difference
        # has no foreign amount, so it carries no "(EUR 0.00)" note.
        activity = self.customer._drkds_statement_data(date(2024, 7, 1), date(2024, 7, 31))
        pay_row = next(r for r in activity["lines"] if r["document"] == payment.move_id.name)
        self.assertAlmostEqual(pay_row["credit"], 40.0, 2)
        self.assertAlmostEqual(pay_row["amount_currency"], -100.0, 2)
        exch_row = next(r for r in activity["lines"] if r["document"] == exchange.name)
        self.assertAlmostEqual(exch_row["credit"], 10.0, 2)
        self.assertFalse(exch_row["currency"])
        self.assertAlmostEqual(activity["closing_balance"], 1670.0, 2)  # 1,720 - 40 - 10

    def test_ageing_fields_need_accounting_rights(self):
        """Like core's ``credit``, the ageing fields are for accounting users only.

        A plain employee cannot read journal items, and a salesman would read
        only his own invoices: neither must be offered the fields.
        """
        employee = new_test_user(self.env, login="stmt_employee", groups="base.group_user")
        fields_seen = self.env["res.partner"].with_user(employee).fields_get()
        for name in ("drkds_stmt_currency_id", "drkds_stmt_0_30", "drkds_stmt_31_60",
                     "drkds_stmt_61_90", "drkds_stmt_90_plus", "drkds_stmt_total_due"):
            self.assertNotIn(name, fields_seen)
        # The contact form still opens for the employee, without the fields.
        form = self.env["res.partner"].with_user(employee).get_views([(False, "form")])
        self.assertNotIn("drkds_stmt", form["views"]["form"]["arch"])
        biller = new_test_user(self.env, login="stmt_fields_biller",
                               groups="account.group_account_invoice")
        self.env.invalidate_all()
        self.assertAlmostEqual(
            self.customer.with_user(biller).drkds_stmt_total_due, 1720.0, 2,
        )

    def test_rendered_html(self):
        """The PDF template renders the figures the engine computed."""
        html = self._render(self.customer, date_from="2024-03-01", date_to="2024-06-30")
        self.assertIn("STATEMENT OF ACCOUNT", html)
        self.assertIn("Meridian Traders", html)
        for text in ("1,000.00", "800.00", "300.00", "650.00", "420.00",
                     "150.00", "1,720.00", "570.00", "500.00"):
            self.assertIn(text, html)
        self.assertIn(self.inv2.name, html)
        # Dates follow the language's date format, like every Odoo document.
        for day in (date(2024, 3, 1), date(2024, 4, 5), date(2024, 6, 30)):
            self.assertIn(format_date(self.env, day), html)
        self.assertNotIn("2024-06-30", html)
        self.assertIn('name="ageing"', html)

    def test_rendered_html_settings(self):
        """Bank details and footer note from settings reach the page."""
        bank = self.env["res.partner.bank"].create({
            "acc_number": "0011223344",
            "partner_id": self.env.company.partner_id.id,
            "bank_id": self.env["res.bank"].create({"name": "Harbour Bank", "bic": "HARBINBB"}).id,
        })
        self.env.company.write({
            "drkds_statement_bank_id": bank.id,
            "drkds_statement_note": "Please quote the invoice number when paying.",
        })
        html = self._render(self.customer, date_from="2024-03-01", date_to="2024-06-30")
        self.assertIn("account 0011223344, Harbour Bank (HARBINBB)", html)
        self.assertIn("Please quote the invoice number when paying.", html)

    def test_removed_bank_account_is_not_printed(self):
        """Deleting a bank account archives it in Odoo 19 and keeps the setting.

        A statement must not send customers to an account the company has
        removed.
        """
        bank = self.env["res.partner.bank"].create({
            "acc_number": "0099887766", "partner_id": self.env.company.partner_id.id,
        })
        self.env.company.drkds_statement_bank_id = bank
        bank.unlink()
        self.assertTrue(bank.exists())
        self.assertFalse(bank.active)
        self.assertEqual(self.env.company.drkds_statement_bank_id, bank)
        html = self._render(self.customer, date_from="2024-03-01", date_to="2024-06-30")
        self.assertNotIn("0099887766", html)
        self.assertNotIn("Please remit to", html)

    def test_report_needs_period(self):
        """Printing without the wizard's period is refused, not rendered empty."""
        with self.assertRaises(UserError):
            self.env["ir.actions.report"]._render_qweb_html(
                "drkds_customer_statement.action_report_drkds_statement",
                self.customer.ids, data={},
            )

    def test_wizard_validation(self):
        wizard = self.env["drkds.statement.wizard"].create({
            "partner_ids": [(6, 0, self.customer.ids)],
            "date_from": "2024-06-30",
            "date_to": "2024-06-30",
        })
        with self.assertRaises(UserError):
            wizard.write({"date_from": "2024-07-01"})
        no_mail = self.env["res.partner"].create({"name": "Silent Partner"})
        wizard = self.env["drkds.statement.wizard"].create({
            "partner_ids": [(6, 0, no_mail.ids)],
            "date_from": "2024-06-01",
            "date_to": "2024-06-30",
        })
        with self.assertRaises(UserError):
            wizard.action_send()

    def test_wizard_print_action(self):
        # A company without a document layout gets the layout configurator
        # from report_action, as core intends; set one as a real company would.
        self.env.company.external_report_layout_id = self.env.ref("web.external_layout_standard")
        wizard = self.env["drkds.statement.wizard"].with_context(
            active_model="res.partner", active_ids=self.customer.ids,
        ).create({"date_from": "2024-03-01", "date_to": "2024-06-30"})
        self.assertEqual(wizard.partner_ids, self.customer)
        action = wizard.action_print()
        self.assertEqual(action["report_name"], "drkds_customer_statement.report_drkds_statement")
        self.assertEqual(action["context"]["active_ids"], self.customer.ids)
        self.assertEqual(action["data"]["date_to"], "2024-06-30")
        self.assertEqual(action["data"]["statement_type"], "activity")

    def test_smart_button_opens_wizard(self):
        action = self.customer.action_drkds_open_statement()
        self.assertEqual(action["res_model"], "drkds.statement.wizard")
        self.assertEqual(action["context"]["default_partner_ids"], [(6, 0, self.customer.ids)])
