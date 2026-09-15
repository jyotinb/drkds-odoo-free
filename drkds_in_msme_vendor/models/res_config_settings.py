from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Expose the MSME payment clock settings in Accounting settings."""

    _inherit = "res.config.settings"

    drkds_msme_agreement_days = fields.Integer(
        related="company_id.drkds_msme_agreement_days", readonly=False,
    )
    drkds_msme_no_agreement_days = fields.Integer(
        related="company_id.drkds_msme_no_agreement_days", readonly=False,
    )
    drkds_msme_due_soon_days = fields.Integer(
        related="company_id.drkds_msme_due_soon_days", readonly=False,
    )
