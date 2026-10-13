"""Print through the same HTTP round trip as the web client."""
import json
from urllib.parse import quote

from odoo import http
from odoo.tests import HttpCase, new_test_user, tagged

from .common import StatementCase


@tagged("post_install", "-at_install")
class TestPrintRoundTrip(StatementCase, HttpCase):

    def test_print_from_the_wizard_downloads_the_statements(self):
        """A report action carrying ``data`` reaches the server without record ids.

        The web client fetches it as ``/report/pdf/<report>?options=..&context=..``
        (``getReportUrl`` in web/static/src/webclient/actions/reports/utils.js)
        through ``/report/download``, so the report receives ``docids=None``
        and must find its partners in ``data``.
        """
        self.env.company.external_report_layout_id = self.env.ref("web.external_layout_standard")
        lotus = self.env["res.partner"].create({"name": "Lotus Supplies", "is_company": True})
        self._invoice("2024-06-12", 1250.0, partner=lotus)
        biller = new_test_user(self.env, login="stmt_print", password="stmt_print_pwd",
                               groups="account.group_account_invoice")
        self.authenticate("stmt_print", "stmt_print_pwd")

        action = self._wizard(self.customer + lotus, user=biller).action_print()
        url = "/report/pdf/%s?options=%s&context=%s" % (
            action["report_name"],
            quote(json.dumps(action["data"])),
            quote(json.dumps(action["context"])),
        )
        response = self.url_open("/report/download", data={
            "data": json.dumps([url, action["report_type"]]),
            "context": json.dumps({"lang": "en_US"}),
            "csrf_token": http.Request.csrf_token(self),
        })
        self.assertEqual(response.status_code, 200)
        # In tests the PDF engine falls back to the HTML it would have printed.
        body = response.content.decode()
        self.assertEqual(body.count("STATEMENT OF ACCOUNT"), 2)
        self.assertIn("Meridian Traders", body)
        self.assertIn("1,720.00", body)
        self.assertIn("Lotus Supplies", body)
        self.assertIn("1,250.00", body)
