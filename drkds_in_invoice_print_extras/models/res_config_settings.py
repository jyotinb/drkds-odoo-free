from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Exposes the invoice declaration in the Accounting settings page."""

    _inherit = "res.config.settings"

    drkds_in_invoice_declaration = fields.Text(
        related="company_id.drkds_in_invoice_declaration",
        string="Invoice Declaration",
        readonly=False,
    )
