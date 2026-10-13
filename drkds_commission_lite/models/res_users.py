from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    drkds_commission_rate = fields.Float(
        string="Default Commission (%)", digits=(5, 2), default=0.0,
        help="Percentage of the untaxed invoiced amount paid to this salesperson "
             "unless a product-category rate overrides it. Zero means no commission.",
    )
    drkds_commission_rate_ids = fields.One2many(
        "drkds.commission.rate", "user_id", string="Category Commission Rates",
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["drkds_commission_rate", "drkds_commission_rate_ids"]
