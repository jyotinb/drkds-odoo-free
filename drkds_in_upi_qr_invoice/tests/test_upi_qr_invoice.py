import unittest
from urllib.parse import parse_qs, urlsplit

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


def _qr_backend_available():
    """True when reportlab can actually rasterise a barcode to PNG.

    reportlab needs a renderPM backend (``_rl_renderPM`` or ``rlPyCairo``) to
    produce a bitmap. Plenty of installs ship reportlab without one, and then
    every barcode and QR code in Odoo fails to render, core's included. Tests
    that need a real image are skipped rather than failed, so this module's
    logic can still be verified on such a host.
    """
    try:
        from odoo.tools.barcode import createBarcodeDrawing

        drawing = createBarcodeDrawing(
            "QR", value="test", format="png", width=32, height=32
        )
        # createBarcodeDrawing only builds the vector Drawing. Rasterising is
        # where the missing backend actually bites, so force it here.
        drawing.asString("png")
    except Exception:
        return False
    return True


QR_BACKEND = _qr_backend_available()
needs_qr_backend = unittest.skipUnless(
    QR_BACKEND, "reportlab has no renderPM backend: install rlPyCairo"
)


@tagged("post_install", "-at_install")
class TestUpiQrInvoice(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.inr = cls.env.ref("base.INR")
        cls.inr.active = True
        cls.company = cls.company_data["company"]
        cls.company.write({
            "drkds_upi_vpa": "acme@okhdfcbank",
            "drkds_upi_payee_name": "Acme & Sons",
        })

    # -- helpers -------------------------------------------------------
    def _invoice(self, move_type="out_invoice", post=True, price=1000.0):
        move = self.env["account.move"].create({
            "move_type": move_type,
            "partner_id": self.partner_a.id,
            "currency_id": self.inr.id,
            "invoice_date": "2026-01-15",
            "invoice_line_ids": [(0, 0, {
                "name": "Service",
                "quantity": 1,
                "price_unit": price,
                "tax_ids": [],
            })],
        })
        if post:
            move.action_post()
        return move

    def _params(self, url):
        split = urlsplit(url)
        self.assertEqual(split.scheme, "upi")
        self.assertEqual(split.netloc, "pay")
        return {k: v[0] for k, v in parse_qs(split.query).items()}

    # -- UPI ID validation ---------------------------------------------
    def test_valid_upi_ids_accepted(self):
        for vpa in (
            "acme@okhdfcbank",
            "acme.industries@ybl",
            "acme-1_2@paytm",
            "9876543210@upi",
        ):
            self.company.drkds_upi_vpa = vpa
            self.assertEqual(self.company.drkds_upi_vpa, vpa)

    def test_upi_id_is_normalised(self):
        self.company.drkds_upi_vpa = "  ACME@OkHdfcBank "
        self.assertEqual(self.company.drkds_upi_vpa, "acme@okhdfcbank")

    def test_blank_upi_id_allowed(self):
        """A blank UPI ID is legitimate. It only means no QR code."""
        self.company.drkds_upi_vpa = False
        self.assertFalse(self.company.drkds_upi_vpa)

    def test_bad_upi_ids_refused(self):
        for vpa in (
            "acme",                 # no handle
            "acme@",                # empty handle
            "@okhdfcbank",          # empty name
            "acme@@okhdfcbank",     # two separators
            "ac me@okhdfcbank",     # space
            "acme@1bank",           # handle must start with a letter
            "a@b",                  # too short on both sides
            "acme@ok_hdfc",         # underscore is not a handle character
        ):
            with self.assertRaises(ValidationError, msg=vpa):
                self.company.drkds_upi_vpa = vpa

    # -- deep link -----------------------------------------------------
    def test_deep_link_parameters(self):
        invoice = self._invoice()
        params = self._params(invoice._drkds_upi_payment_url())
        self.assertEqual(params["pa"], "acme@okhdfcbank")
        self.assertEqual(params["pn"], "Acme & Sons")
        self.assertEqual(params["am"], "1000.00")
        self.assertEqual(params["cu"], "INR")
        self.assertEqual(params["tr"], invoice.name)
        self.assertEqual(params["tn"], "Invoice %s" % invoice.name)

    def test_deep_link_is_url_encoded(self):
        """A payee name with an ampersand must not split the query string."""
        url = self._invoice()._drkds_upi_payment_url()
        self.assertIn("pn=Acme%20%26%20Sons", url)
        self.assertNotIn("Acme & Sons", url)
        self.assertNotIn("+", url)

    def test_amount_is_the_residual_not_the_total(self):
        invoice = self._invoice()
        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=invoice.ids,
        ).create({"amount": 400.0})._create_payments()
        params = self._params(invoice._drkds_upi_payment_url())
        self.assertEqual(params["am"], "600.00")

    def test_amount_omitted_when_toggle_off(self):
        self.company.drkds_upi_include_amount = False
        params = self._params(self._invoice()._drkds_upi_payment_url())
        self.assertNotIn("am", params)
        self.assertEqual(params["cu"], "INR")

    def test_reference_omitted_when_toggle_off(self):
        self.company.drkds_upi_include_reference = False
        params = self._params(self._invoice()._drkds_upi_payment_url())
        self.assertNotIn("tr", params)
        self.assertNotIn("tn", params)

    def test_payment_reference_wins_over_name(self):
        invoice = self._invoice(post=False)
        invoice.payment_reference = "REF/2026/007"
        invoice.action_post()
        params = self._params(invoice._drkds_upi_payment_url())
        self.assertEqual(params["tr"], "REF/2026/007")
        self.assertIn("REF%2F2026%2F007", invoice._drkds_upi_payment_url())

    # -- eligibility ---------------------------------------------------
    def test_no_qr_without_upi_id(self):
        self.company.drkds_upi_vpa = False
        invoice = self._invoice()
        self.assertFalse(invoice.drkds_upi_qr_available)
        self.assertFalse(invoice._drkds_upi_payment_url())
        self.assertFalse(invoice._drkds_upi_qr_data_uri())

    def test_no_qr_on_draft_invoice(self):
        self.assertFalse(self._invoice(post=False).drkds_upi_qr_available)

    def test_no_qr_on_vendor_bill(self):
        bill = self._invoice(move_type="in_invoice")
        self.assertFalse(bill.drkds_upi_qr_available)
        self.assertFalse(bill._drkds_upi_payment_url())

    def test_no_qr_on_credit_note(self):
        note = self._invoice(move_type="out_refund")
        self.assertFalse(note.drkds_upi_qr_available)
        self.assertFalse(note._drkds_upi_payment_url())

    def test_no_qr_on_paid_invoice(self):
        invoice = self._invoice()
        self.assertTrue(invoice.drkds_upi_qr_available)
        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=invoice.ids,
        ).create({})._create_payments()
        self.assertEqual(invoice.payment_state, "paid")
        self.assertFalse(invoice.drkds_upi_qr_available)
        self.assertFalse(invoice._drkds_upi_payment_url())

    def test_no_amount_bearing_qr_outside_inr(self):
        """UPI carries INR only, so a foreign currency invoice gets no QR."""
        invoice = self._invoice()
        invoice.state = "draft"
        invoice.currency_id = self.env.ref("base.USD")
        invoice.action_post()
        self.assertFalse(invoice.drkds_upi_qr_available)

    # -- rendering -----------------------------------------------------
    @needs_qr_backend
    def test_qr_image_is_rendered_by_odoo(self):
        data_uri = self._invoice()._drkds_upi_qr_data_uri()
        self.assertTrue(data_uri.startswith("data:image/png;base64,"))
        self.assertGreater(len(data_uri), 200)

    @needs_qr_backend
    def test_qr_appears_in_the_invoice_pdf_html(self):
        invoice = self._invoice()
        html = self.env["ir.actions.report"]._render_qweb_html(
            "account.report_invoice", invoice.ids,
        )[0].decode()
        self.assertIn("drkds_upi_qrcode", html)
        self.assertIn("acme@okhdfcbank", html)

    def test_no_qr_block_in_the_pdf_of_a_vendor_bill(self):
        bill = self._invoice(move_type="in_invoice")
        html = self.env["ir.actions.report"]._render_qweb_html(
            "account.report_invoice", bill.ids,
        )[0].decode()
        self.assertNotIn("drkds_upi_qrcode", html)
