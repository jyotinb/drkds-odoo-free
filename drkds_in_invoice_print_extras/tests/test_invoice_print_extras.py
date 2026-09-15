"""Behaviour tests for the Indian invoice print extras.

Every test renders the real invoice report through the report engine. The
whole module is a set of additions to a template, so a helper that returns the
right value into a block that never renders would be worthless: the assertions
are made against the produced HTML.

Two of the tests exist to prove a negative - that the localisation's own GST
blocks still render, and that no second report action was created - because
duplicating core is the failure mode this module was rescoped to avoid.
"""

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged

#: The localisation's invoice report. We deliberately render *this*, not a
#: report of our own, because we do not have one.
REPORT = "account.account_invoices"


def _has_renderpm():
    """Return True when reportlab can actually rasterise a drawing to PNG.

    Building the drawing succeeds even with no backend installed; only
    ``asString("png")`` reveals the missing rasteriser, so the probe has to go
    all the way through to the image.
    """
    try:
        from reportlab.graphics.barcode import createBarcodeDrawing

        createBarcodeDrawing("QR", value="probe", width=64, height=64).asString("png")
    except Exception:
        return False
    return True


@tagged("post_install", "-at_install")
class TestInvoicePrintExtras(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("in")
    def setUpClass(cls):
        super().setUpClass()
        # The shipping address block in core carries
        # groups="account.group_delivery_invoice_address", so the shipping
        # state code we add inside it is only visible to users who can see the
        # delivery address at all. That is the right behaviour; the test user
        # just needs the group to be able to observe it.
        cls.env.user.group_ids |= cls.env.ref("account.group_delivery_invoice_address")

        cls.state_gj = cls.env.ref("base.state_in_gj")
        cls.state_mh = cls.env.ref("base.state_in_mh")
        cls.country_in = cls.env.ref("base.in")

        cls.company = cls.company_data["company"]
        cls.company.write({
            "state_id": cls.state_gj.id,
            "vat": "24AAGCC7144L6ZE",
            "street": "Khodiyar Chowk",
            "city": "Amreli",
            "zip": "365220",
            "l10n_in_is_gst_registered": True,
        })

        ChartTemplate = cls.env["account.chart.template"]
        cls.gst_18 = ChartTemplate.ref("sgst_sale_18")
        cls.igst_18 = ChartTemplate.ref("igst_sale_18")

        cls.partner = cls.env["res.partner"].create({
            "name": "Rajkot Buyer",
            "vat": "24ABCPM8965E1ZE",
            "country_id": cls.country_in.id,
            "state_id": cls.state_gj.id,
            "street": "Karansinhji Rd",
            "city": "Rajkot",
            "zip": "360001",
        })
        cls.partner_mh = cls.env["res.partner"].create({
            "name": "Mumbai Buyer",
            "vat": "27DJMPM8965E1ZE",
            "country_id": cls.country_in.id,
            "state_id": cls.state_mh.id,
            "city": "Mumbai",
            "zip": "400052",
        })
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.product = cls.env["product.product"].create({
            "name": "Widget",
            "uom_id": cls.uom_unit.id,
            "lst_price": 1000.0,
            "l10n_in_hsn_code": "847130",
        })

    # -- helpers -------------------------------------------------------
    def _draft_invoice(self, partner=None, taxes=None, shipping=None):
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": (partner or self.partner).id,
            "partner_shipping_id": (shipping or partner or self.partner).id,
            "invoice_date": "2026-04-10",
            "invoice_date_due": "2026-05-10",
            "invoice_line_ids": [Command.create({
                "product_id": self.product.id,
                "quantity": 2.0,
                "price_unit": 1000.0,
                "product_uom_id": self.uom_unit.id,
                "tax_ids": [Command.set((taxes or self.gst_18).ids)],
            })],
        })
        return move

    def _invoice(self, partner=None, taxes=None, shipping=None):
        """A posted invoice, which is what customers actually print."""
        move = self._draft_invoice(partner=partner, taxes=taxes, shipping=shipping)
        move.action_post()
        return move

    def _render(self, move):
        html, _rtype = self.env["ir.actions.report"]._render_qweb_html(REPORT, move.ids)
        return html.decode() if isinstance(html, bytes) else html

    # -- we extend core, we do not duplicate it ------------------------
    def test_no_second_report_action_is_created(self):
        """The module must not add a print entry of its own."""
        ours = self.env["ir.actions.report"].search([
            ("report_name", "like", "drkds_in_invoice_print_extras%"),
        ])
        self.assertFalse(ours, "This module must extend the standard report, not add one.")

    def test_localisation_blocks_still_render(self):
        """l10n_in's own GST output is untouched by our additions."""
        move = self._invoice()
        html = self._render(move)
        # The title, HSN column and HSN summary are core's work, not ours.
        self.assertIn("Tax Invoice", html)
        self.assertIn("HSN Summary", html)
        self.assertIn("847130", html)
        self.assertIn("Place of supply", html)

    def test_report_used_is_the_localisation_one(self):
        move = self._invoice()
        self.assertEqual(
            move._get_name_invoice_report(),
            "l10n_in.l10n_in_report_invoice_document_inherit",
        )

    # -- 1. state codes ------------------------------------------------
    def test_supplier_state_code_is_printed(self):
        move = self._invoice()
        html = self._render(move)
        self.assertIn("Supplier State:", html)
        self.assertIn("Gujarat", html)
        self.assertIn("Code 24", html)

    def test_buyer_state_code_is_printed(self):
        move = self._invoice(partner=self.partner_mh, taxes=self.igst_18)
        html = self._render(move)
        self.assertIn("Code 27", html)

    def test_place_of_supply_gains_its_code(self):
        """Core prints the place of supply; we append the state code to it."""
        move = self._invoice(partner=self.partner_mh, taxes=self.igst_18)
        html = self._render(move)
        self.assertRegex(html, r"Place of supply:\s*<span[^>]*>Maharashtra</span>\s*\(Code")

    def test_shipping_state_code_is_printed(self):
        """The shipping state code rides along with the shipping address block.

        That block is gated on ``account.group_delivery_invoice_address`` in
        core, so the code follows the same visibility rather than leaking a
        delivery address to users who may not see one.
        """
        move = self._invoice(partner=self.partner, shipping=self.partner_mh,
                             taxes=self.gst_18)
        html = self._render(move)
        # Both the billing (24) and the shipping (27) state codes appear.
        self.assertIn("Code 24", html)
        self.assertIn("Code 27", html)

    def test_state_without_tin_still_renders(self):
        """A state carrying no GST code degrades to the bare name.

        The invoice is left in draft on purpose. l10n_in refuses to post an
        invoice whose place of supply has no TIN (``_post`` in
        ``l10n_in/models/account_invoice.py``), so a posted invoice can never
        reach this state. Draft is where the missing-code path is genuinely
        reachable, and the report has to survive it.
        """
        self.state_gj.l10n_in_tin = False
        move = self._draft_invoice()
        html = self._render(move)
        self.assertIn("Supplier State:", html)
        self.assertIn("Gujarat", html)
        self.assertNotIn("(Code ", html)

    def test_partner_without_state_renders(self):
        self.partner.state_id = False
        move = self._invoice()
        self.assertIn("Tax Invoice", self._render(move))

    # -- 2. bank block -------------------------------------------------
    def _make_bank_account(self, partner):
        bank = self.env["res.bank"].create({
            "name": "Demo Bank, Amreli Branch",
            "bic": "DEMO0000123",
        })
        return self.env["res.partner.bank"].create({
            "acc_number": "500100200300",
            "partner_id": partner.id,
            "bank_id": bank.id,
        })

    def test_bank_block_prints_ifsc_and_branch(self):
        account = self._make_bank_account(self.company.partner_id)
        move = self._invoice()
        move.partner_bank_id = account

        html = self._render(move)
        self.assertIn("Bank Details", html)
        self.assertIn("Account Holder:", html)
        self.assertIn("500100200300", html)
        self.assertIn("IFSC:", html)
        self.assertIn("DEMO0000123", html)
        self.assertIn("Branch:", html)
        self.assertIn("Demo Bank, Amreli Branch", html)

    def test_bank_block_falls_back_to_company_account(self):
        """With no recipient bank on the invoice, the company account is used."""
        self._make_bank_account(self.company.partner_id)
        move = self._invoice()
        move.partner_bank_id = False

        self.assertTrue(move.drkds_in_bank_account())
        self.assertIn("500100200300", self._render(move))

    def test_no_bank_anywhere_renders_without_the_block(self):
        self.company.partner_id.bank_ids.unlink()
        move = self._invoice()
        move.partner_bank_id = False

        html = self._render(move)
        self.assertFalse(move.drkds_in_bank_account())
        self.assertNotIn("Bank Details", html)
        self.assertIn("Tax Invoice", html)

    def test_bank_without_bank_record_renders(self):
        """An account with no bank behind it prints the number and no IFSC."""
        account = self.env["res.partner.bank"].create({
            "acc_number": "900900900900",
            "partner_id": self.company.partner_id.id,
        })
        move = self._invoice()
        move.partner_bank_id = account

        html = self._render(move)
        self.assertIn("900900900900", html)
        self.assertNotIn("IFSC:", html)

    # -- 3. declaration ------------------------------------------------
    def test_declaration_default_is_printed(self):
        self.assertTrue(self.company.drkds_in_invoice_declaration)
        move = self._invoice()
        html = self._render(move)
        self.assertIn("Declaration", html)
        self.assertIn("actual price of the goods", html)

    def test_declaration_is_configurable(self):
        self.company.drkds_in_invoice_declaration = "Subject to Amreli jurisdiction."
        move = self._invoice()
        self.assertIn("Subject to Amreli jurisdiction.", self._render(move))

    def test_empty_declaration_prints_nothing(self):
        self.company.drkds_in_invoice_declaration = False
        move = self._invoice()
        html = self._render(move)
        self.assertNotIn("Declaration", html)
        self.assertIn("Tax Invoice", html)

    def test_declaration_reachable_from_settings(self):
        settings = self.env["res.config.settings"].sudo().create({})
        settings.drkds_in_invoice_declaration = "From settings."
        settings.execute()
        self.assertEqual(self.company.drkds_in_invoice_declaration, "From settings.")

    # -- 4. signature --------------------------------------------------
    def test_signature_block_names_the_company(self):
        move = self._invoice()
        html = self._render(move)
        self.assertIn("Authorised Signatory", html)
        self.assertIn(self.company.name, html)

    # -- 5. reverse charge marker --------------------------------------
    def test_reverse_charge_marker_hidden_by_default(self):
        move = self._invoice()
        self.assertFalse(move.drkds_in_has_reverse_charge)
        self.assertNotIn("Reverse Charge:", self._render(move))

    def test_reverse_charge_marker_shown_when_tax_is_flagged(self):
        rcm_tax = self.igst_18.copy({"name": "IGST 18% RCM"})
        rcm_tax.l10n_in_reverse_charge = True
        move = self._invoice(partner=self.partner_mh, taxes=rcm_tax)

        self.assertTrue(move.drkds_in_has_reverse_charge)
        html = self._render(move)
        self.assertIn("Reverse Charge:", html)
        self.assertIn("tax payable by recipient", html)

    # -- gating --------------------------------------------------------
    def test_extras_hidden_when_company_is_not_gst_registered(self):
        """Printing a GST state code for a non-registered company is wrong."""
        self.company.l10n_in_is_gst_registered = False
        move = self._invoice()

        self.assertFalse(move.drkds_in_show_print_extras)
        html = self._render(move)
        self.assertNotIn("Supplier State:", html)
        self.assertNotIn("Bank Details", html)
        self.assertNotIn("Authorised Signatory", html)

    def test_extras_shown_for_registered_indian_company(self):
        move = self._invoice()
        self.assertTrue(move.drkds_in_show_print_extras)

    # -- the whole pipeline --------------------------------------------
    def test_render_to_pdf(self):
        """The full PDF pipeline produces a PDF document.

        Skipped where reportlab has no renderPM backend. The invoice
        rasterises a QR code, and without ``rlPyCairo`` or ``_rl_renderPM``
        nothing in Odoo can turn a drawing into an image. That is a missing
        system package, not a defect in this module, so the test skips rather
        than reporting a failure it cannot fix.
        """
        if not _has_renderpm():
            self.skipTest("reportlab has no renderPM backend on this host")
        account = self._make_bank_account(self.company.partner_id)
        move = self._invoice()
        move.partner_bank_id = account
        pdf, _rtype = self.env["ir.actions.report"]._render_qweb_pdf(REPORT, move.ids)
        self.assertTrue(pdf.startswith(b"%PDF"))
