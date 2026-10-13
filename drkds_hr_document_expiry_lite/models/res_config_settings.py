from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    drkds_hr_document_responsible_id = fields.Many2one(
        related="company_id.drkds_hr_document_responsible_id", readonly=False,
    )
