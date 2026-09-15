"""Expose the e-way bill watch settings in the Accounting settings page."""
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    drkds_eway_km_per_day = fields.Integer(
        related="company_id.drkds_eway_km_per_day", readonly=False,
    )
    drkds_eway_threshold = fields.Float(
        related="company_id.drkds_eway_threshold", readonly=False,
    )
