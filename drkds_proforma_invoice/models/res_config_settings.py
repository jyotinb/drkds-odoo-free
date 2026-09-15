from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Exposes the proforma disclaimer in Sales settings."""

    _inherit = "res.config.settings"

    drkds_proforma_disclaimer = fields.Text(
        related="company_id.drkds_proforma_disclaimer",
        string="Proforma Disclaimer",
        readonly=False,
    )
