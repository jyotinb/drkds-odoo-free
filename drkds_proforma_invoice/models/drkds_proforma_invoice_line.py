from odoo import api, fields, models


class DrkdsProformaInvoiceLine(models.Model):
    """One priced line of a proforma invoice.

    The line stores its own copy of the product, description, quantity, price
    and taxes taken from the source document. It is a snapshot: changing the
    quotation afterwards does not silently rewrite a proforma that has already
    been handed to a customer.
    """

    _name = "drkds.proforma.invoice.line"
    _description = "Proforma Invoice Line"
    _order = "proforma_id, sequence, id"

    proforma_id = fields.Many2one(
        "drkds.proforma.invoice", string="Proforma Invoice",
        required=True, ondelete="cascade", index=True,
    )
    sequence = fields.Integer(default=10)
    display_type = fields.Selection(
        [("line_section", "Section"), ("line_note", "Note")],
        default=False,
        help="Set for a section or note line, which carries no amounts.",
    )
    product_id = fields.Many2one("product.product", string="Product")
    name = fields.Text(string="Description", required=True)
    quantity = fields.Float(
        string="Quantity", default=1.0, digits="Product Unit of Measure",
    )
    product_uom_id = fields.Many2one("uom.uom", string="Unit")
    price_unit = fields.Float(string="Unit Price", digits="Product Price")
    discount = fields.Float(string="Discount (%)", digits="Discount")
    tax_ids = fields.Many2many(
        "account.tax", string="Taxes",
        help="Shown for information only. A proforma recognises no tax.",
    )

    currency_id = fields.Many2one(
        related="proforma_id.currency_id", store=True, readonly=True,
    )
    company_id = fields.Many2one(
        related="proforma_id.company_id", store=True, readonly=True,
    )
    partner_id = fields.Many2one(
        related="proforma_id.partner_id", store=True, readonly=True,
    )

    price_subtotal = fields.Monetary(
        string="Subtotal", compute="_compute_amounts", store=True,
        currency_field="currency_id",
    )
    price_tax = fields.Monetary(
        string="Tax", compute="_compute_amounts", store=True,
        currency_field="currency_id",
    )
    price_total = fields.Monetary(
        string="Total", compute="_compute_amounts", store=True,
        currency_field="currency_id",
    )

    @api.depends(
        "quantity", "price_unit", "discount", "tax_ids", "currency_id",
        "display_type",
    )
    def _compute_amounts(self):
        """Price the line for display.

        ``compute_all`` is used purely as a calculator. Nothing here is written
        to an accounting model: the result lands on this line and on the
        proforma totals only.
        """
        for line in self:
            if line.display_type:
                line.price_subtotal = line.price_tax = line.price_total = 0.0
                continue
            net = line.price_unit * (1.0 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_ids.compute_all(
                net,
                currency=line.currency_id or None,
                quantity=line.quantity,
                product=line.product_id or None,
                partner=line.partner_id or None,
            )
            line.price_subtotal = taxes["total_excluded"]
            line.price_total = taxes["total_included"]
            line.price_tax = taxes["total_included"] - taxes["total_excluded"]

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self:
            if not line.product_id:
                continue
            line.name = line.product_id.get_product_multiline_description_sale()
            line.product_uom_id = line.product_id.uom_id
            line.price_unit = line.product_id.lst_price
