"""Month-end statements for two customers, printed and sent from the wizard."""
from datetime import date

from odoo.addons.mail.tests.common import MockEmail
from odoo.tools.misc import format_date
from odoo.tests import tagged

from .common import StatementCase


@tagged("post_install", "-at_install")
class TestScenario(StatementCase, MockEmail):
    """June 2024 closes. Accounts runs statements for two customers at once.

    Meridian Traders is the fixture customer (closing 1,720.00). Lotus Supplies
    is new this quarter:

        INV-A 2024-05-20  2,400.00   paid 2,400.00 on 2024-06-03
        INV-B 2024-06-12  1,250.00
        INV-C 2024-06-28    310.00

    So Lotus opens June at 2,400.00, and closes at 1,560.00, all in 0-30.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.lotus = cls.env["res.partner"].create({
            "name": "Lotus Supplies",
            "email": "finance@lotus.example.com",
            "is_company": True,
        })
        cls.lotus_a = cls._invoice("2024-05-20", 2400.0, partner=cls.lotus, ref="PO-118")
        cls.lotus_b = cls._invoice("2024-06-12", 1250.0, partner=cls.lotus)
        cls.lotus_c = cls._invoice("2024-06-28", 310.0, partner=cls.lotus)
        cls._pay(cls.lotus_a, "2024-06-03", 2400.0)

    def test_month_end_statements(self):
        wizard = self.env["drkds.statement.wizard"].with_context(
            active_model="res.partner",
            active_ids=(self.customer + self.lotus).ids,
        ).create({"date_from": "2024-06-01", "date_to": "2024-06-30"})
        self.assertEqual(wizard.partner_ids, self.customer + self.lotus)

        # 1. The figures behind each statement.
        meridian = self.customer._drkds_statement_data(date(2024, 6, 1), date(2024, 6, 30))
        self.assertAlmostEqual(meridian["opening_balance"], 1150.0, 2)  # 500 + 650
        self.assertAlmostEqual(meridian["closing_balance"], 1720.0, 2)
        lotus = self.lotus._drkds_statement_data(date(2024, 6, 1), date(2024, 6, 30))
        self.assertAlmostEqual(lotus["opening_balance"], 2400.0, 2)
        self.assertEqual(
            [(r["date"], r["debit"], r["credit"], r["balance"]) for r in lotus["lines"]],
            [
                (date(2024, 6, 3), 0.0, 2400.0, 0.0),
                (date(2024, 6, 12), 1250.0, 0.0, 1250.0),
                (date(2024, 6, 28), 310.0, 0.0, 1560.0),
            ],
        )
        self.assertAlmostEqual(lotus["closing_balance"], 1560.0, 2)
        self.assertAlmostEqual(lotus["ageing"]["b0_30"], 1560.0, 2)
        self.assertAlmostEqual(lotus["ageing"]["total"], 1560.0, 2)
        # INV-A predates June, so its reference shows on a statement that starts in May.
        may = self.lotus._drkds_statement_data(date(2024, 5, 1), date(2024, 6, 30))
        self.assertEqual(may["lines"][0]["reference"], "PO-118")
        self.assertAlmostEqual(may["opening_balance"], 0.0, 2)

        # 2. One rendered document per customer, each with its own figures.
        html = self._render(self.customer + self.lotus, date_from="2024-05-01", date_to="2024-06-30")
        self.assertEqual(html.count("STATEMENT OF ACCOUNT"), 2)
        self.assertIn("Meridian Traders", html)
        self.assertIn("Lotus Supplies", html)
        self.assertIn("1,720.00", html)
        self.assertIn("1,560.00", html)
        self.assertIn("2,400.00", html)
        self.assertIn("PO-118", html)

        # 3. Send: one chatter message with the PDF, one email per customer.
        with self.mock_mail_gateway():
            wizard.action_send()
        for partner, label in ((self.customer, "Meridian"), (self.lotus, "Lotus")):
            attachments = self.env["ir.attachment"].search([
                ("res_model", "=", "res.partner"), ("res_id", "=", partner.id),
                ("mimetype", "=", "application/pdf"),
            ])
            self.assertEqual(len(attachments), 1)
            self.assertIn(label, attachments.name)
            self.assertIn("2024-06-30", attachments.name)
            message = partner.message_ids.filtered(lambda m: attachments in m.attachment_ids)
            self.assertEqual(len(message), 1)
            self.assertEqual(message.message_type, "comment")
            self.assertIn("Statement of Account", message.subject)
            self.assertIn(partner.name, message.subject)
            # The template prints dates in the recipient's locale format.
            self.assertIn(format_date(self.env, date(2024, 6, 1)), message.body)
            self.assertIn(format_date(self.env, date(2024, 6, 30)), message.body)
            self.assertIn("for the period", message.body)
            self.assertIn(partner, message.partner_ids)
            mail = self._new_mails.filtered(lambda m: m.mail_message_id == message)
            self.assertEqual(len(mail), 1)
            self.assertIn(attachments, mail.attachment_ids)
            self.assertIn(partner, mail.recipient_ids)
        self.assertEqual(len(self._new_mails), 2)
        sent_to = " ".join(addr for m in self._mails for addr in m["email_to"])
        self.assertIn(self.customer.email, sent_to)
        self.assertIn(self.lotus.email, sent_to)

        # 4. Outstanding-only run for the same date, which Lotus asked for.
        outstanding = self.lotus._drkds_statement_data(
            date(2024, 6, 1), date(2024, 6, 30), "outstanding",
        )
        self.assertEqual(
            [(r["document"], r["debit"]) for r in outstanding["lines"]],
            [(self.lotus_b.name, 1250.0), (self.lotus_c.name, 310.0)],
        )
        self.assertAlmostEqual(outstanding["closing_balance"], 1560.0, 2)
