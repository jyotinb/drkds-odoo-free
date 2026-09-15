from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    drkds_upi_vpa = fields.Char(
        related="company_id.drkds_upi_vpa", readonly=False,
    )
    drkds_upi_payee_name = fields.Char(
        related="company_id.drkds_upi_payee_name", readonly=False,
    )
    drkds_upi_include_amount = fields.Boolean(
        related="company_id.drkds_upi_include_amount", readonly=False,
    )
    drkds_upi_include_reference = fields.Boolean(
        related="company_id.drkds_upi_include_reference", readonly=False,
    )
