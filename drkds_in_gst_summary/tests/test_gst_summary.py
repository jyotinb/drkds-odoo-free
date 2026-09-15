"""Behaviour tests for the GST period summary.

The point of every test here is a number a preparer would recompute by hand:
which bucket a supply lands in, what the tax split inside that bucket is, and
whether a document belongs to the period at all.
"""

from datetime import date

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install", "post_install_l10n")
class TestDrkdsGstSummary(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country("in")
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.state_gj = cls.env.ref("base.state_in_gj")
        cls.state_mh = cls.env.ref("base.state_in_mh")
        cls.country_in = cls.env.ref("base.in")
        cls.company.write({
            "state_id": cls.state_gj.id,
            "vat": "24AAGCC7144L6ZE",
            "l10n_in_is_gst_registered": True,
        })

        ChartTemplate = cls.env["account.chart.template"]
        cls.gst_18 = ChartTemplate.ref("sgst_sale_18")  # CGST 9 + SGST 9
        cls.igst_5 = ChartTemplate.ref("igst_sale_5")
        cls.gst_purchase_5 = ChartTemplate.ref("sgst_purchase_5")

        # Same state as the company: an intra-state supply.
        cls.partner_intra = cls.env["res.partner"].create({
            "name": "Intra State Customer",
            "vat": "24ABCPM8965E1ZE",
            "country_id": cls.country_in.id,
            "state_id": cls.state_gj.id,
        })
        # Another state: an inter-state supply.
        cls.partner_inter = cls.env["res.partner"].create({
            "name": "Inter State Customer",
            "vat": "27DJMPM8965E1ZE",
            "country_id": cls.country_in.id,
            "state_id": cls.state_mh.id,
        })

        cls.product_hsn_a = cls.env["product.product"].create({
            "name": "Widget",
            "l10n_in_hsn_code": "847130",
            "lst_price": 1000.0,
            "standard_price": 1000.0,
        })
        cls.product_hsn_b = cls.env["product.product"].create({
            "name": "Gadget",
            "l10n_in_hsn_code": "901890",
            "lst_price": 500.0,
            "standard_price": 500.0,
        })

        cls.period_from = date(2024, 4, 1)
        cls.period_to = date(2024, 4, 30)
        cls.in_period = date(2024, 4, 10)
        cls.out_of_period = date(2024, 5, 10)

    # -- helpers -------------------------------------------------------
    @classmethod
    def _invoice(cls, move_type, partner, tax, product, quantity, price, invoice_date):
        move = cls.env["account.move"].create({
            "move_type": move_type,
            "partner_id": partner.id,
            "invoice_date": invoice_date,
            "date": invoice_date,
            "invoice_line_ids": [Command.create({
                "product_id": product.id,
                "quantity": quantity,
                "price_unit": price,
                "tax_ids": [Command.set(tax.ids)],
            })],
        })
        move.action_post()
        return move

    def _summary(self, date_from=None, date_to=None):
        summary = self.env["drkds.gst.summary"].create({
            "date_from": date_from or self.period_from,
            "date_to": date_to or self.period_to,
            "company_id": self.company.id,
        })
        summary.action_compute()
        return summary

    @staticmethod
    def _bucket(summary, direction, rate, state=None):
        lines = summary.line_ids.filtered(
            lambda l: l.summary_type == direction
            and abs(l.tax_rate - rate) < 0.01
            and (state is None or l.state_id == state)
        )
        return lines

    # -- outward: rate and place of supply ----------------------------
    def test_outward_splits_intra_and_inter_state_by_rate(self):
        """An 18% intra-state and a 5% inter-state supply land in two buckets.

        Intra-state 18% on 10 000 is CGST 900 + SGST 900 and no IGST.
        Inter-state 5% on 4 000 is IGST 200 and no CGST or SGST.
        """
        self._invoice("out_invoice", self.partner_intra, self.gst_18,
                      self.product_hsn_a, 10, 1000.0, self.in_period)
        self._invoice("out_invoice", self.partner_inter, self.igst_5,
                      self.product_hsn_b, 8, 500.0, self.in_period)

        summary = self._summary()
        intra = self._bucket(summary, "outward", 18.0, self.state_gj)
        self.assertEqual(len(intra), 1, "one 18% Gujarat bucket")
        self.assertAlmostEqual(intra.taxable_value, 10000.0)
        self.assertAlmostEqual(intra.cgst_amount, 900.0)
        self.assertAlmostEqual(intra.sgst_amount, 900.0)
        self.assertAlmostEqual(intra.igst_amount, 0.0)
        self.assertAlmostEqual(intra.cess_amount, 0.0)
        self.assertEqual(intra.supply_type, "intra")

        inter = self._bucket(summary, "outward", 5.0, self.state_mh)
        self.assertEqual(len(inter), 1, "one 5% Maharashtra bucket")
        self.assertAlmostEqual(inter.taxable_value, 4000.0)
        self.assertAlmostEqual(inter.igst_amount, 200.0)
        self.assertAlmostEqual(inter.cgst_amount, 0.0)
        self.assertAlmostEqual(inter.sgst_amount, 0.0)
        self.assertEqual(inter.supply_type, "inter")

        self.assertAlmostEqual(summary.outward_taxable, 14000.0)
        self.assertAlmostEqual(summary.outward_cgst, 900.0)
        self.assertAlmostEqual(summary.outward_sgst, 900.0)
        self.assertAlmostEqual(summary.outward_igst, 200.0)

    def test_two_invoices_same_rate_and_state_merge(self):
        """Buckets are per rate and state, not per document."""
        self._invoice("out_invoice", self.partner_intra, self.gst_18,
                      self.product_hsn_a, 1, 1000.0, self.in_period)
        self._invoice("out_invoice", self.partner_intra, self.gst_18,
                      self.product_hsn_b, 1, 3000.0, self.in_period)

        summary = self._summary()
        bucket = self._bucket(summary, "outward", 18.0, self.state_gj)
        self.assertEqual(len(bucket), 1)
        self.assertAlmostEqual(bucket.taxable_value, 4000.0)
        self.assertEqual(bucket.move_count, 2, "both documents are counted")
        self.assertEqual(len(bucket.move_ids), 2, "drill-down reaches both")

    # -- HSN ----------------------------------------------------------
    def test_hsn_summary_aggregates_quantity_and_value(self):
        """The same HSN on two invoices is one row with summed quantity."""
        self._invoice("out_invoice", self.partner_intra, self.gst_18,
                      self.product_hsn_a, 10, 1000.0, self.in_period)
        self._invoice("out_invoice", self.partner_intra, self.gst_18,
                      self.product_hsn_a, 4, 1000.0, self.in_period)
        self._invoice("out_invoice", self.partner_intra, self.gst_18,
                      self.product_hsn_b, 3, 500.0, self.in_period)

        summary = self._summary()
        outward_hsn = summary.hsn_line_ids.filtered(
            lambda l: l.summary_type == "outward")
        row_a = outward_hsn.filtered(lambda l: l.hsn_code == "847130")
        self.assertEqual(len(row_a), 1, "one row per HSN, UQC and rate")
        self.assertAlmostEqual(row_a.quantity, 14.0)
        self.assertAlmostEqual(row_a.taxable_value, 14000.0)
        self.assertAlmostEqual(row_a.cgst_amount, 1260.0)
        self.assertAlmostEqual(row_a.sgst_amount, 1260.0)
        self.assertAlmostEqual(row_a.tax_rate, 18.0)
        self.assertTrue(row_a.uqc, "a UQC or unit name is always reported")

        row_b = outward_hsn.filtered(lambda l: l.hsn_code == "901890")
        self.assertAlmostEqual(row_b.quantity, 3.0)
        self.assertAlmostEqual(row_b.taxable_value, 1500.0)

        # The HSN table and the rate table describe the same supplies.
        self.assertAlmostEqual(
            sum(outward_hsn.mapped("taxable_value")), summary.outward_taxable)

    def test_hsn_row_drills_down_to_its_documents(self):
        invoice = self._invoice("out_invoice", self.partner_intra, self.gst_18,
                                self.product_hsn_a, 2, 1000.0, self.in_period)
        summary = self._summary()
        row = summary.hsn_line_ids.filtered(
            lambda l: l.summary_type == "outward" and l.hsn_code == "847130")
        action = row.action_open_moves()
        self.assertEqual(action["res_model"], "account.move")
        self.assertIn(invoice.id, action["domain"][0][2])

    # -- credit notes --------------------------------------------------
    def test_credit_note_reduces_outward_totals(self):
        """A credit note is subtracted from the period, not listed apart."""
        self._invoice("out_invoice", self.partner_intra, self.gst_18,
                      self.product_hsn_a, 10, 1000.0, self.in_period)
        self._invoice("out_refund", self.partner_intra, self.gst_18,
                      self.product_hsn_a, 2, 1000.0, self.in_period)

        summary = self._summary()
        buckets = self._bucket(summary, "outward", 18.0, self.state_gj)

        # GSTR-1 reports credit notes in their own CDNR table, so the summary
        # keeps them in their own row rather than silently netting them off.
        invoice_row = buckets.filtered(
            lambda l: l.gstr_section == "sale_b2b_regular")
        credit_row = buckets.filtered(
            lambda l: l.gstr_section == "sale_cdnr_regular")
        self.assertEqual(len(invoice_row), 1)
        self.assertEqual(len(credit_row), 1, "the credit note has its own row")
        self.assertAlmostEqual(invoice_row.taxable_value, 10000.0)
        self.assertAlmostEqual(credit_row.taxable_value, -2000.0,
                               msg="a credit note carries a negative value")
        self.assertAlmostEqual(credit_row.cgst_amount, -180.0)
        self.assertAlmostEqual(credit_row.sgst_amount, -180.0)

        # What it must not do is inflate the period.
        self.assertAlmostEqual(sum(buckets.mapped("taxable_value")), 8000.0)
        self.assertAlmostEqual(sum(buckets.mapped("cgst_amount")), 720.0)
        self.assertAlmostEqual(sum(buckets.mapped("sgst_amount")), 720.0)
        self.assertAlmostEqual(summary.outward_taxable, 8000.0)
        self.assertAlmostEqual(summary.outward_cgst, 720.0)
        self.assertAlmostEqual(summary.outward_sgst, 720.0)

        hsn_row = summary.hsn_line_ids.filtered(
            lambda l: l.summary_type == "outward" and l.hsn_code == "847130")
        self.assertAlmostEqual(hsn_row.quantity, 8.0)
        self.assertAlmostEqual(hsn_row.taxable_value, 8000.0)

    # -- inward --------------------------------------------------------
    def test_inward_bills_are_summarised_separately(self):
        """Vendor bills fill the inward table and leave the outward one alone."""
        self._invoice("out_invoice", self.partner_intra, self.gst_18,
                      self.product_hsn_a, 1, 1000.0, self.in_period)
        self._invoice("in_invoice", self.partner_intra, self.gst_purchase_5,
                      self.product_hsn_b, 4, 500.0, self.in_period)

        summary = self._summary()
        inward = summary.line_ids.filtered(lambda l: l.summary_type == "inward")
        self.assertEqual(len(inward), 1)
        self.assertAlmostEqual(inward.taxable_value, 2000.0)
        self.assertAlmostEqual(inward.tax_rate, 5.0)
        self.assertAlmostEqual(inward.cgst_amount, 50.0)
        self.assertAlmostEqual(inward.sgst_amount, 50.0)
        self.assertAlmostEqual(summary.inward_taxable, 2000.0)
        self.assertAlmostEqual(summary.outward_taxable, 1000.0)

    # -- period --------------------------------------------------------
    def test_date_range_excludes_out_of_period_documents(self):
        """A May invoice never reaches an April summary."""
        self._invoice("out_invoice", self.partner_intra, self.gst_18,
                      self.product_hsn_a, 1, 1000.0, self.in_period)
        later = self._invoice("out_invoice", self.partner_intra, self.gst_18,
                              self.product_hsn_a, 1, 7000.0, self.out_of_period)

        april = self._summary()
        self.assertAlmostEqual(april.outward_taxable, 1000.0)
        self.assertNotIn(later.id, april.line_ids.move_ids.ids)

        may = self._summary(date(2024, 5, 1), date(2024, 5, 31))
        self.assertAlmostEqual(may.outward_taxable, 7000.0)

    def test_draft_documents_are_excluded_unless_asked_for(self):
        """A GST return is filed from posted documents."""
        draft = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner_intra.id,
            "invoice_date": self.in_period,
            "date": self.in_period,
            "invoice_line_ids": [Command.create({
                "product_id": self.product_hsn_a.id,
                "quantity": 1,
                "price_unit": 2500.0,
                "tax_ids": [Command.set(self.gst_18.ids)],
            })],
        })
        self.assertEqual(draft.state, "draft")

        summary = self._summary()
        self.assertAlmostEqual(summary.outward_taxable, 0.0)

        with_draft = self.env["drkds.gst.summary"].create({
            "date_from": self.period_from,
            "date_to": self.period_to,
            "company_id": self.company.id,
            "include_draft": True,
        })
        with_draft.action_compute()
        self.assertAlmostEqual(with_draft.outward_taxable, 2500.0)

    # -- reconciliation aid --------------------------------------------
    def test_b2b_and_b2c_split_follows_the_recipient_gstin(self):
        """GSTR-1 separates registered from unregistered recipients."""
        unregistered = self.env["res.partner"].create({
            "name": "Walk-in Customer",
            "country_id": self.country_in.id,
            "state_id": self.state_gj.id,
        })
        self._invoice("out_invoice", self.partner_intra, self.gst_18,
                      self.product_hsn_a, 1, 3000.0, self.in_period)
        self._invoice("out_invoice", unregistered, self.gst_18,
                      self.product_hsn_a, 1, 1000.0, self.in_period)

        summary = self._summary()
        self.assertAlmostEqual(summary.outward_b2b_taxable, 3000.0)
        self.assertAlmostEqual(summary.outward_b2c_taxable, 1000.0)
        self.assertAlmostEqual(
            summary.outward_b2b_taxable + summary.outward_b2c_taxable,
            summary.outward_taxable,
        )

    # -- export --------------------------------------------------------
    def test_export_produces_a_file(self):
        """Export uses a library already in the install; it never adds one."""
        self._invoice("out_invoice", self.partner_intra, self.gst_18,
                      self.product_hsn_a, 1, 1000.0, self.in_period)
        summary = self._summary()
        action = summary.action_export()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertTrue(summary.xlsx_file)
        self.assertTrue(summary.xlsx_filename)

    def test_summary_line_drill_down_returns_its_moves(self):
        invoice = self._invoice("out_invoice", self.partner_inter, self.igst_5,
                                self.product_hsn_b, 2, 500.0, self.in_period)
        summary = self._summary()
        line = self._bucket(summary, "outward", 5.0, self.state_mh)
        action = line.action_open_moves()
        self.assertEqual(action["res_model"], "account.move")
        self.assertEqual(action["domain"][0][2], [invoice.id])
