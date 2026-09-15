from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import html2plaintext


class SaleOrder(models.Model):
    """Lets a quotation produce a proforma invoice.

    The proforma is built by reading the order. No field of the order is
    written, no invoice is created and no invoice sequence is touched.
    """

    _inherit = "sale.order"

    drkds_proforma_ids = fields.One2many(
        "drkds.proforma.invoice", "sale_order_id", string="Proforma Invoices",
    )
    drkds_proforma_count = fields.Integer(
        string="Proforma Count", compute="_compute_drkds_proforma_count",
    )

    @api.depends("drkds_proforma_ids")
    def _compute_drkds_proforma_count(self):
        for order in self:
            order.drkds_proforma_count = len(order.drkds_proforma_ids)

    def _prepare_drkds_proforma_values(self):
        """Build the proforma header from this order."""
        self.ensure_one()
        return {
            "partner_id": self.partner_invoice_id.id or self.partner_id.id,
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "user_id": self.user_id.id or self.env.user.id,
            "sale_order_id": self.id,
            "validity_date": self.validity_date,
            "terms": self.payment_term_id.name or False,
            "note": html2plaintext(self.note) if self.note else False,
        }

    def _prepare_drkds_proforma_line_values(self, line):
        """Copy one order line onto the proforma."""
        return {
            "sequence": line.sequence,
            "display_type": line.display_type or False,
            "product_id": line.product_id.id,
            "name": line.name,
            "quantity": 0.0 if line.display_type else line.product_uom_qty,
            "product_uom_id": line.product_uom_id.id,
            "price_unit": 0.0 if line.display_type else line.price_unit,
            "discount": 0.0 if line.display_type else line.discount,
            "tax_ids": [(6, 0, [] if line.display_type else line.tax_ids.ids)],
        }

    def drkds_create_proforma(self):
        """Create and return one proforma invoice per order in ``self``."""
        proformas = self.env["drkds.proforma.invoice"]
        for order in self:
            if order.state == "cancel":
                raise UserError(_(
                    "Quotation %s is cancelled, so it cannot produce a proforma "
                    "invoice.", order.display_name,
                ))
            if not order.order_line:
                raise UserError(_(
                    "Quotation %s has no lines.", order.display_name,
                ))
            values = order._prepare_drkds_proforma_values()
            values["line_ids"] = [
                (0, 0, order._prepare_drkds_proforma_line_values(line))
                for line in order.order_line
            ]
            proformas |= proformas.create(values)
        return proformas

    def action_drkds_create_proforma(self):
        """Button: build a proforma and open it."""
        proformas = self.drkds_create_proforma()
        return {
            "type": "ir.actions.act_window",
            "name": _("Proforma Invoice"),
            "res_model": "drkds.proforma.invoice",
            "res_id": proformas[:1].id,
            "view_mode": "form",
        }

    def action_drkds_view_proformas(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Proforma Invoices"),
            "res_model": "drkds.proforma.invoice",
            "domain": [("sale_order_id", "=", self.id)],
            "view_mode": "list,form",
            "context": {"create": False},
        }

    def _create_invoices(self, grouped=False, final=False, date=None):
        """Standard invoicing flow, plus the proforma conversion trail.

        The proforma is only ever a reader here: ``super()`` creates the real
        invoice exactly as Odoo would without this module.
        """
        moves = super()._create_invoices(grouped=grouped, final=final, date=date)
        for move in moves:
            orders = move.line_ids.sale_line_ids.order_id
            proformas = orders.drkds_proforma_ids.filtered(
                lambda p: p.state in ("draft", "issued")
            )
            if proformas:
                proformas._mark_converted(move)
        return moves
