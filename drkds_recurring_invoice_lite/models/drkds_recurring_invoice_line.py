from odoo import Command, api, fields, models


class DrkdsRecurringInvoiceLine(models.Model):
    """One line of the invoice template, copied onto every generated invoice."""

    _name = "drkds.recurring.invoice.line"
    _description = "Recurring Invoice Template Line"
    _order = "recurring_id, sequence, id"
    _check_company_auto = True

    recurring_id = fields.Many2one(
        "drkds.recurring.invoice", string="Template", required=True,
        ondelete="cascade", index=True,
    )
    company_id = fields.Many2one(
        related="recurring_id.company_id", store=True, readonly=True,
    )
    currency_id = fields.Many2one(
        related="recurring_id.currency_id", store=True, readonly=True,
    )
    partner_id = fields.Many2one(
        related="recurring_id.partner_id", store=True, readonly=True,
    )
    sequence = fields.Integer(default=10)
    display_type = fields.Selection(
        [("line_section", "Section"), ("line_note", "Note")], default=False,
    )
    # check_company supplies the company part of these domains, parent
    # companies included, so a branch sees its parent's products and taxes.
    product_id = fields.Many2one(
        "product.product", string="Product", check_company=True,
        domain="[('sale_ok', '=', True)]",
    )
    name = fields.Text(string="Description", required=True)
    quantity = fields.Float(
        string="Quantity", default=1.0, digits="Product Unit of Measure",
    )
    product_uom_id = fields.Many2one("uom.uom", string="Unit")
    price_unit = fields.Float(string="Unit Price", digits="Product Price")
    tax_ids = fields.Many2many(
        "account.tax", string="Taxes", check_company=True,
        domain="[('type_tax_use', '=', 'sale')]",
    )
    price_subtotal = fields.Monetary(
        string="Subtotal", compute="_compute_amounts", store=True,
        currency_field="currency_id",
    )
    price_total = fields.Monetary(
        string="Total", compute="_compute_amounts", store=True,
        currency_field="currency_id",
    )

    @api.depends("quantity", "price_unit", "tax_ids", "currency_id", "display_type")
    def _compute_amounts(self):
        for line in self:
            if line.display_type:
                line.price_subtotal = line.price_total = 0.0
                continue
            res = line.tax_ids.compute_all(
                line.price_unit,
                currency=line.currency_id or None,
                quantity=line.quantity,
                product=line.product_id or None,
                partner=line.partner_id or None,
            )
            line.price_subtotal = res["total_excluded"]
            line.price_total = res["total_included"]

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self:
            product = line.product_id
            if not product:
                continue
            company = line.company_id or self.env.company
            line.name = product.get_product_multiline_description_sale()
            line.product_uom_id = product.uom_id
            # Same helpers as an invoice line: the list price converted into
            # the template's currency, and the product's taxes of this company
            # or, for a branch, of the nearest parent that has some.
            line.price_unit = product._get_tax_included_unit_price(
                company,
                line.currency_id or company.currency_id,
                line.recurring_id.next_date or fields.Date.context_today(line),
                "sale",
                product_uom=product.uom_id,
            )
            line.tax_ids = product.taxes_id._filter_taxes_by_company(company)

    def _prepare_invoice_line_vals(self, fiscal_position=None):
        """Values of the invoice line, taxes mapped by ``fiscal_position``."""
        self.ensure_one()
        if self.display_type:
            return {
                "display_type": self.display_type,
                "name": self.name,
                "sequence": self.sequence,
            }
        return {
            "sequence": self.sequence,
            "product_id": self.product_id.id,
            "name": self.name,
            "quantity": self.quantity,
            "product_uom_id": self.product_uom_id.id or self.product_id.uom_id.id,
            "price_unit": self.price_unit,
            "tax_ids": [Command.set(
                (fiscal_position or self.env["account.fiscal.position"]).map_tax(self.tax_ids).ids
            )],
        }
