from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Exposes the statement bank account and footer note in Invoicing settings."""

    _inherit = "res.config.settings"

    drkds_statement_bank_id = fields.Many2one(
        related="company_id.drkds_statement_bank_id", readonly=False,
    )
    drkds_statement_note = fields.Text(
        related="company_id.drkds_statement_note", readonly=False,
    )
