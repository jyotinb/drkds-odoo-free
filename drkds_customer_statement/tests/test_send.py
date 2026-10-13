"""Send by Email: who may send, who receives it, and how the PDFs are rendered."""
from unittest.mock import patch

from odoo.addons.base.models.ir_actions_report import IrActionsReport
from odoo.addons.mail.tests.common import MockEmail
from odoo.exceptions import AccessError, UserError
from odoo.tests import new_test_user, tagged

from .common import REPORT_REF, StatementCase


@tagged("post_install", "-at_install")
class TestSend(StatementCase, MockEmail):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.external_report_layout_id = cls.env.ref("web.external_layout_standard")
        cls.lotus = cls.env["res.partner"].create({
            "name": "Lotus Supplies", "email": "finance@lotus.example.com", "is_company": True,
        })
        cls._invoice("2024-06-12", 1250.0, partner=cls.lotus)

    def _statement_messages(self, partner):
        return partner.message_ids.filtered(
            lambda m: m.message_type == "comment" and m.attachment_ids
        )

    def test_billing_user_without_contact_rights_sends(self):
        """Billing alone is enough to send; the sender stays the author.

        A new internal user in Odoo 19 gets no Contact Creation right, so a
        Billing user cannot write contacts, which posting on a contact's
        chatter would otherwise require.
        """
        biller = new_test_user(self.env, login="stmt_biller",
                               groups="account.group_account_invoice")
        self.assertFalse(biller.has_group("base.group_partner_manager"))
        with self.mock_mail_gateway():
            self._wizard(self.customer, user=biller).action_send()
        message = self._statement_messages(self.customer)
        self.assertEqual(len(message), 1)
        self.assertEqual(message.author_id, biller.partner_id)
        self.assertEqual(message.attachment_ids.res_model, "res.partner")
        self.assertEqual(message.attachment_ids.res_id, self.customer.id)
        self.assertEqual(len(self._new_mails), 1)

    def test_readonly_user_prints_but_cannot_send(self):
        auditor = new_test_user(self.env, login="stmt_auditor",
                                groups="account.group_account_readonly")
        arch = self.env["drkds.statement.wizard"].with_user(auditor).get_views(
            [(False, "form")])["views"]["form"]["arch"]
        self.assertIn('name="action_print"', arch)
        self.assertNotIn('name="action_send"', arch)
        wizard = self._wizard(self.customer, user=auditor)
        action = wizard.action_print()
        html = self.env["ir.actions.report"].with_user(auditor)._render_qweb_html(
            REPORT_REF, None, data=action["data"])[0].decode()
        self.assertIn("1,720.00", html)
        with self.assertRaises(AccessError):
            wizard.action_send()
        self.assertFalse(self._statement_messages(self.customer))

    def test_only_the_recipients_are_notified(self):
        """Followers of the contact (here a colleague) are not sent the statement."""
        colleague = new_test_user(self.env, login="stmt_colleague", groups="base.group_user",
                                  email="colleague@company.example.com")
        self.customer.message_subscribe(partner_ids=colleague.partner_id.ids)
        with self.mock_mail_gateway():
            self._wizard(self.customer).action_send()
        message = self._statement_messages(self.customer)
        notified = self.env["mail.notification"].search([("mail_message_id", "=", message.id)])
        self.assertEqual(notified.res_partner_id, self.customer)
        self.assertEqual(self._new_mails.recipient_ids, self.customer)

    def test_email_goes_to_the_selected_contact(self):
        """The statement covers the company; the email goes to the contact chosen."""
        holding = self.env["res.partner"].create({"name": "Harbour Holdings", "is_company": True})
        meera = self.env["res.partner"].create({
            "name": "Meera Iyer", "parent_id": holding.id, "email": "meera@harbour.example.com",
        })
        self._invoice("2024-06-10", 99.0, partner=holding)
        with self.mock_mail_gateway():
            self._wizard(meera).action_send()
        message = self._statement_messages(holding)
        self.assertEqual(len(message), 1)
        self.assertEqual(message.partner_ids, meera)
        self.assertIn("Harbour Holdings", message.subject)
        self.assertIn("99.00", message.attachment_ids.raw.decode())
        self.assertEqual(self._new_mails.recipient_ids, meera)
        self.assertFalse(self._statement_messages(meera))

    def test_selected_contact_without_email_is_named(self):
        """The check is on the person who would receive it, not on the company."""
        holding = self.env["res.partner"].create({
            "name": "Quiet Holdings", "is_company": True, "email": "info@quiet.example.com",
        })
        ravi = self.env["res.partner"].create({"name": "Ravi Menon", "parent_id": holding.id})
        with self.assertRaisesRegex(UserError, "Ravi Menon"):
            self._wizard(ravi).action_send()
        self.assertFalse(self._statement_messages(holding))

    def test_one_rendering_for_all_partners(self):
        """Send renders every statement in one run, then splits it per partner.

        In tests the PDF engine falls back to HTML, so the single run shows up
        as a single HTML rendering of both partners.
        """
        calls = []
        original = IrActionsReport._render_qweb_html

        def spy(report_model, report_ref, docids, data=None):
            calls.append(list(docids or []))
            return original(report_model, report_ref, docids, data=data)

        with patch.object(IrActionsReport, "_render_qweb_html", spy), self.mock_mail_gateway():
            self._wizard(self.customer + self.lotus).action_send()
        self.assertEqual(calls, [(self.customer + self.lotus).ids])
        for partner, own, other in (
            (self.customer, "Meridian Traders", "Lotus Supplies"),
            (self.lotus, "Lotus Supplies", "Meridian Traders"),
        ):
            html = self._statement_messages(partner).attachment_ids.raw.decode()
            self.assertIn(own, html)
            self.assertNotIn(other, html)
        self.assertEqual(len(self._new_mails), 2)

    def test_second_company_statement_is_sent_in_its_name(self):
        """The subject names the company whose statement it is, not the sender's."""
        company_2 = self.setup_other_company(name="Coastal Statement Co")["company"]
        self._invoice("2024-06-14", 300.0, company=company_2)
        wizard = self._wizard(self.customer, company_id=company_2.id).with_context(
            allowed_company_ids=(self.env.company + company_2).ids,
        )
        with self.mock_mail_gateway():
            wizard.action_send()
        message = self._statement_messages(self.customer)
        self.assertIn("Coastal Statement Co", message.subject)
        self.assertNotIn(self.env.company.name, message.subject)
        self.assertIn("300.00", message.attachment_ids.raw.decode())
        self.assertNotIn("1,720.00", message.attachment_ids.raw.decode())
