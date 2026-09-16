from odoo import fields, models


class SaleOrder(models.Model):
    """Branch on a sales order, defaulted from the salesperson's user."""

    _inherit = "sale.order"

    drkds_branch_id = fields.Many2one(
        "drkds.lite.branch", string="Branch",
        default=lambda self: self.env.user._drkds_default_branch(),
        index="btree_not_null",
        domain="[('company_id', '=', company_id)]",
        check_company=False,
        tracking=True,
        help="Branch that raised this order. Carried onto the invoice.",
    )

    def _prepare_invoice(self):
        """Carry the order's branch onto the invoice it creates."""
        vals = super()._prepare_invoice()
        if self.drkds_branch_id:
            vals["drkds_branch_id"] = self.drkds_branch_id.id
        return vals
