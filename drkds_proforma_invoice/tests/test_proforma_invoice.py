from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from ..models.drkds_proforma_invoice import ACCOUNTING_LINK_FIELDS


@tagged("post_install", "-at_install")
class TestProformaInvoice(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Proforma = cls.env["drkds.proforma.invoice"]
        cls.Move = cls.env["account.move"]
        cls.company = cls.env.company
        cls.partner = cls.env["res.partner"].create({"name": "Acme Trading"})
        cls.tax = cls.env["account.tax"].create({
            "name": "Proforma Test Tax 10%",
            "amount_type": "percent",
            "amount": 10.0,
            "type_tax_use": "sale",
            "company_id": cls.company.id,
        })
        cls.product_a = cls.env["product.product"].create({
            "name": "Widget A", "type": "consu", "list_price": 100.0,
            "invoice_policy": "order",
        })
        cls.product_b = cls.env["product.product"].create({
            "name": "Widget B", "type": "consu", "list_price": 250.0,
            "invoice_policy": "order",
        })
        cls.order = cls._make_order(cls.env.company.currency_id)

    @classmethod
    def _pricelist_for(cls, currency):
        """A pricelist in ``currency``; a sale order takes its currency from it."""
        return cls.env["product.pricelist"].create({
            "name": f"Proforma test {currency.name}",
            "currency_id": currency.id,
            "company_id": cls.company.id,
        })

    @classmethod
    def _make_order(cls, currency, discount=0.0):
        order = cls.env["sale.order"].create({
            "partner_id": cls.partner.id,
            "pricelist_id": cls._pricelist_for(currency).id,
            "order_line": [
                (0, 0, {
                    "product_id": cls.product_a.id,
                    "product_uom_qty": 3.0,
                    "price_unit": 100.0,
                    "discount": discount,
                    "tax_ids": [(6, 0, cls.tax.ids)],
                }),
                (0, 0, {
                    "product_id": cls.product_b.id,
                    "product_uom_qty": 2.0,
                    "price_unit": 250.0,
                    "tax_ids": [(6, 0, cls.tax.ids)],
                }),
            ],
        })
        # The pricelist drives the price; the test fixes its own unit prices.
        order.order_line[0].price_unit = 100.0
        order.order_line[0].discount = discount
        order.order_line[1].price_unit = 250.0
        return order

    # -- copying from a sale order -------------------------------------
    def test_proforma_copies_lines_and_totals(self):
        """Every order line lands on the proforma with the same amounts."""
        proforma = self.order.drkds_create_proforma()
        self.assertEqual(len(proforma), 1)
        self.assertEqual(len(proforma.line_ids), len(self.order.order_line))
        self.assertEqual(proforma.partner_id, self.partner)
        self.assertEqual(proforma.sale_order_id, self.order)
        self.assertEqual(proforma.state, "draft")

        for order_line, pf_line in zip(self.order.order_line, proforma.line_ids):
            self.assertEqual(pf_line.product_id, order_line.product_id)
            self.assertEqual(pf_line.quantity, order_line.product_uom_qty)
            self.assertEqual(pf_line.price_unit, order_line.price_unit)
            self.assertEqual(pf_line.tax_ids, order_line.tax_ids)

        self.assertAlmostEqual(proforma.amount_untaxed, self.order.amount_untaxed, 2)
        self.assertAlmostEqual(proforma.amount_tax, self.order.amount_tax, 2)
        self.assertAlmostEqual(proforma.amount_total, self.order.amount_total, 2)
        self.assertAlmostEqual(proforma.amount_untaxed, 800.0, 2)
        self.assertAlmostEqual(proforma.amount_total, 880.0, 2)

    def test_proforma_is_a_snapshot(self):
        """Editing the quotation afterwards does not rewrite an issued proforma."""
        proforma = self.order.drkds_create_proforma()
        proforma.action_issue()
        self.order.order_line[0].price_unit = 999.0
        self.assertEqual(proforma.line_ids[0].price_unit, 100.0)

    def test_discount_is_carried_over(self):
        order = self._make_order(self.company.currency_id, discount=10.0)
        proforma = order.drkds_create_proforma()
        self.assertEqual(proforma.line_ids[0].discount, 10.0)
        # 3 x 100 less 10% = 270, plus 2 x 250 = 500 -> 770 untaxed.
        self.assertAlmostEqual(proforma.amount_untaxed, 770.0, 2)

    # -- the ledger guarantee ------------------------------------------
    def test_proforma_creates_no_account_move(self):
        """Creating and issuing a proforma leaves the ledger untouched."""
        moves_before = self.Move.search_count([])
        lines_before = self.env["account.move.line"].search_count([])
        proforma = self.order.drkds_create_proforma()
        proforma.action_issue()
        self.assertEqual(self.Move.search_count([]), moves_before)
        self.assertEqual(
            self.env["account.move.line"].search_count([]), lines_before
        )
        self.assertFalse(proforma.invoice_id)
        self.assertFalse(self.order.invoice_ids)

    def test_model_holds_no_accounting_data(self):
        """Structural check: the model owns no accounting field it could post.

        The only relations to accounting models are the read-only links to the
        source draft invoice and to the invoice that superseded the proforma.
        There is no journal, no account and no accounting line, so no code path
        can turn a proforma into a journal entry.
        """
        accounting_fields = self.Proforma._accounting_fields()
        self.assertEqual(sorted(accounting_fields), sorted(ACCOUNTING_LINK_FIELDS))
        for name in accounting_fields:
            self.assertTrue(
                self.Proforma._fields[name].readonly,
                f"{name} must stay read-only",
            )
        line_accounting = {
            name for name, field in
            self.env["drkds.proforma.invoice.line"]._fields.items()
            if getattr(field, "comodel_name", None) in (
                "account.move", "account.move.line", "account.journal",
                "account.account",
            )
        }
        self.assertFalse(line_accounting)

    def test_proforma_refuses_to_be_posted(self):
        """An automation that calls action_post gets a clear error, not a move."""
        proforma = self.order.drkds_create_proforma()
        with self.assertRaises(UserError):
            proforma.action_post()

    def test_no_journal_is_touched(self):
        """No journal's entry count changes when a proforma is issued."""
        journals = self.env["account.journal"].search([])
        before = {
            j.id: self.Move.search_count([("journal_id", "=", j.id)])
            for j in journals
        }
        self.order.drkds_create_proforma().action_issue()
        after = {
            j.id: self.Move.search_count([("journal_id", "=", j.id)])
            for j in journals
        }
        self.assertEqual(before, after)

    # -- numbering ------------------------------------------------------
    def test_proforma_numbering_is_independent_of_invoices(self):
        """A proforma never consumes an invoice number.

        A real invoice is posted, its number recorded, then a proforma is
        issued, then a second invoice is posted. The second invoice must follow
        the first without a gap.
        """
        self.order.action_confirm()
        first_invoice = self.order._create_invoices()
        first_invoice.action_post()
        first_number = first_invoice.name

        proforma = self.order.drkds_create_proforma()
        proforma.action_issue()
        self.assertTrue(proforma.name.startswith("PRO/"))

        second_order = self._make_order(self.company.currency_id)
        second_order.action_confirm()
        second_invoice = second_order._create_invoices()
        second_invoice.action_post()

        self.assertEqual(
            second_invoice.journal_id, first_invoice.journal_id,
            "The test only means something on a single journal.",
        )
        prefix, _sep, number = first_number.rpartition("/")
        expected = f"{prefix}/{str(int(number) + 1).zfill(len(number))}"
        self.assertEqual(
            second_invoice.name, expected,
            "The invoice sequence skipped a number because of the proforma.",
        )

    def test_proforma_sequence_increments_on_its_own(self):
        first = self.order.drkds_create_proforma()
        second = self._make_order(self.company.currency_id).drkds_create_proforma()
        self.assertNotEqual(first.name, second.name)
        self.assertTrue(first.name.startswith("PRO/"))
        self.assertTrue(second.name.startswith("PRO/"))

    # -- conversion -----------------------------------------------------
    def test_conversion_links_the_real_invoice(self):
        proforma = self.order.drkds_create_proforma()
        proforma.action_issue()
        self.order.action_confirm()
        invoice = self.order._create_invoices()
        self.assertEqual(proforma.state, "converted")
        self.assertEqual(proforma.invoice_id, invoice)

    def test_cancelled_proforma_is_not_converted(self):
        proforma = self.order.drkds_create_proforma()
        proforma.action_cancel()
        self.order.action_confirm()
        self.order._create_invoices()
        self.assertEqual(proforma.state, "cancelled")
        self.assertFalse(proforma.invoice_id)

    def test_converted_proforma_cannot_be_cancelled_or_deleted(self):
        proforma = self.order.drkds_create_proforma()
        proforma.action_issue()
        self.order.action_confirm()
        self.order._create_invoices()
        with self.assertRaises(UserError):
            proforma.action_cancel()
        with self.assertRaises(UserError):
            proforma.unlink()

    # -- from a draft invoice -------------------------------------------
    def test_proforma_from_draft_invoice(self):
        invoice = self.Move.create({
            "move_type": "out_invoice",
            "partner_id": self.partner.id,
            "invoice_line_ids": [(0, 0, {
                "product_id": self.product_a.id,
                "quantity": 4.0,
                "price_unit": 50.0,
                "tax_ids": [(6, 0, self.tax.ids)],
            })],
        })
        proforma = invoice.drkds_create_proforma()
        self.assertEqual(proforma.source_move_id, invoice)
        self.assertEqual(len(proforma.line_ids), 1)
        self.assertAlmostEqual(proforma.amount_untaxed, 200.0, 2)
        self.assertEqual(invoice.state, "draft")
        self.assertFalse(invoice.name and invoice.name != "/")

    def test_posting_the_source_invoice_converts_the_proforma(self):
        invoice = self.Move.create({
            "move_type": "out_invoice",
            "partner_id": self.partner.id,
            "invoice_line_ids": [(0, 0, {
                "product_id": self.product_a.id,
                "quantity": 1.0,
                "price_unit": 10.0,
            })],
        })
        proforma = invoice.drkds_create_proforma()
        proforma.action_issue()
        invoice.action_post()
        self.assertEqual(proforma.state, "converted")
        self.assertEqual(proforma.invoice_id, invoice)

    def test_posted_invoice_refuses_a_proforma(self):
        invoice = self.Move.create({
            "move_type": "out_invoice",
            "partner_id": self.partner.id,
            "invoice_line_ids": [(0, 0, {
                "product_id": self.product_a.id,
                "quantity": 1.0,
                "price_unit": 10.0,
            })],
        })
        invoice.action_post()
        with self.assertRaises(UserError):
            invoice.drkds_create_proforma()

    # -- workflow -------------------------------------------------------
    def test_workflow_states(self):
        proforma = self.order.drkds_create_proforma()
        self.assertEqual(proforma.state, "draft")
        proforma.action_issue()
        self.assertEqual(proforma.state, "issued")
        with self.assertRaises(UserError):
            proforma.action_issue()
        proforma.action_cancel()
        self.assertEqual(proforma.state, "cancelled")
        proforma.action_draft()
        self.assertEqual(proforma.state, "draft")

    def test_empty_proforma_cannot_be_issued(self):
        proforma = self.Proforma.create({"partner_id": self.partner.id})
        with self.assertRaises(UserError):
            proforma.action_issue()

    def test_cancelled_order_refuses_a_proforma(self):
        order = self._make_order(self.company.currency_id)
        order.action_cancel()
        with self.assertRaises(UserError):
            order.drkds_create_proforma()

    # -- multi-currency --------------------------------------------------
    def test_proforma_keeps_the_order_currency(self):
        """A foreign currency order produces a proforma in that same currency."""
        other = self.env["res.currency"].with_context(active_test=False).search(
            [("id", "!=", self.company.currency_id.id)], limit=1
        )
        other.active = True
        order = self._make_order(other)
        proforma = order.drkds_create_proforma()
        self.assertEqual(proforma.currency_id, other)
        self.assertEqual(proforma.line_ids.mapped("currency_id"), other)
        self.assertAlmostEqual(proforma.amount_untaxed, order.amount_untaxed, 2)
        self.assertNotEqual(proforma.currency_id, self.company.currency_id)

    # -- document --------------------------------------------------------
    def test_disclaimer_defaults_from_the_company(self):
        proforma = self.order.drkds_create_proforma()
        self.assertTrue(proforma.disclaimer)
        self.assertIn("not a tax invoice", proforma.disclaimer.lower())
        self.assertEqual(
            proforma.disclaimer, self.company.drkds_proforma_disclaimer
        )

    def test_pdf_is_rendered_and_says_proforma(self):
        proforma = self.order.drkds_create_proforma()
        proforma.action_issue()
        html, _dummy = self.env["ir.actions.report"]._render_qweb_html(
            "drkds_proforma_invoice.action_report_drkds_proforma_invoice",
            proforma.ids,
        )
        text = html.decode() if isinstance(html, bytes) else html
        self.assertIn("PROFORMA INVOICE", text)
        self.assertIn("not a tax invoice", text.lower())
        self.assertIn(proforma.name, text)

    def test_mail_template_targets_the_proforma(self):
        template = self.env.ref(
            "drkds_proforma_invoice.mail_template_drkds_proforma_invoice"
        )
        self.assertEqual(template.model, "drkds.proforma.invoice")
        proforma = self.order.drkds_create_proforma()
        values = template._render_field("subject", proforma.ids)
        self.assertIn(proforma.name, values[proforma.id])
