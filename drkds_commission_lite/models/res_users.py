from odoo import fields, models


# Pay is confidential: colleagues must not read each other's rates. A user still
# reads their own through SELF_READABLE_FIELDS below.
_RATE_MANAGERS = "sales_team.group_sale_manager,account.group_account_manager"


class ResUsers(models.Model):
    _inherit = "res.users"

    drkds_commission_rate = fields.Float(
        string="Default Commission (%)", digits=(5, 2), default=0.0, groups=_RATE_MANAGERS,
        help="Percentage of the untaxed invoiced amount paid to this salesperson "
             "unless a product-category rate overrides it. Zero means no commission.",
    )
    drkds_commission_rate_ids = fields.One2many(
        "drkds.commission.rate", "user_id", string="Category Commission Rates",
        groups=_RATE_MANAGERS,
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["drkds_commission_rate", "drkds_commission_rate_ids"]
