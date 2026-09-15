from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import html2plaintext


class AccountMove(models.Model):
    """Lets a draft customer invoice produce a proforma invoice.

    Nothing in this file writes to the ledger. The draft invoice is read, a
    separate ``drkds.proforma.invoice`` record is created, and the invoice is
    left exactly as it was - still draft, still holding no number.
    """

    _inherit = "account.move"

    drkds_proforma_ids = fields.One2many(
        "drkds.proforma.invoice", "source_move_id", string="Proforma Invoices",
    )
    drkds_proforma_count = fields.Integer(
        string="Proforma Count", compute="_compute_drkds_proforma_count",
    )

    @api.depends("drkds_proforma_ids")
    def _compute_drkds_proforma_count(self):
        for move in self:
            move.drkds_proforma_count = len(move.drkds_proforma_ids)

    def _prepare_drkds_proforma_values(self):
        self.ensure_one()
        return {
            "partner_id": self.partner_id.id,
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "source_move_id": self.id,
            "date": self.invoice_date or fields.Date.context_today(self),
            "validity_date": self.invoice_date_due,
            "terms": self.invoice_payment_term_id.name or False,
            "note": html2plaintext(self.narration) if self.narration else False,
        }

    def _prepare_drkds_proforma_line_values(self, line):
        return {
            "sequence": line.sequence,
            "display_type": (
                line.display_type
                if line.display_type in ("line_section", "line_note")
                else False
            ),
            "product_id": line.product_id.id,
            "name": line.name or (line.product_id.display_name or "/"),
            "quantity": line.quantity,
            "product_uom_id": line.product_uom_id.id,
            "price_unit": line.price_unit,
            "discount": line.discount,
            "tax_ids": [(6, 0, line.tax_ids.ids)],
        }

    def drkds_create_proforma(self):
        """Create and return one proforma per draft customer invoice."""
        proformas = self.env["drkds.proforma.invoice"]
        for move in self:
            if move.move_type not in ("out_invoice", "out_refund"):
                raise UserError(_(
                    "A proforma invoice can only be drawn from a customer invoice."
                ))
            if move.state != "draft":
                raise UserError(_(
                    "Invoice %s is already posted. A proforma is only useful "
                    "before the real invoice exists.", move.display_name,
                ))
            lines = move.invoice_line_ids.filtered(
                lambda line: line.display_type in (
                    "product", "line_section", "line_note", False,
                )
            )
            if not lines:
                raise UserError(_("Invoice %s has no lines.", move.display_name))
            values = move._prepare_drkds_proforma_values()
            values["line_ids"] = [
                (0, 0, move._prepare_drkds_proforma_line_values(line))
                for line in lines
            ]
            proformas |= proformas.create(values)
        return proformas

    def action_drkds_create_proforma(self):
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
            "domain": [("source_move_id", "=", self.id)],
            "view_mode": "list,form",
            "context": {"create": False},
        }

    def _post(self, soft=True):
        """Post the real invoice, then close out any proforma it replaces."""
        posted = super()._post(soft=soft)
        for move in posted:
            proformas = move.drkds_proforma_ids.filtered(
                lambda p: p.state in ("draft", "issued")
            )
            if proformas:
                proformas._mark_converted(move)
        return posted
