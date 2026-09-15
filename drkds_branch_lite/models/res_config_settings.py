from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    drkds_branch_invoice_sequence = fields.Boolean(
        related="company_id.drkds_branch_invoice_sequence",
        string="Branch-wise Invoice Numbering",
        readonly=False,
    )
