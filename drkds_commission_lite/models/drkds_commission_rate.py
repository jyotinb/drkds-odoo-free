from odoo import api, fields, models
from odoo.exceptions import ValidationError


class DrkdsCommissionRate(models.Model):
    """A commission percentage for one salesperson on one product category.

    It overrides the salesperson's default rate for products in that category
    or in any of its sub-categories. The nearest ancestor wins.
    """
    _name = "drkds.commission.rate"
    _description = "Commission Rate per Product Category"
    _order = "user_id, categ_id"
    _check_company_auto = True

    user_id = fields.Many2one(
        "res.users", string="Salesperson", required=True, index=True, ondelete="cascade",
        domain=[("share", "=", False)],
    )
    categ_id = fields.Many2one(
        "product.category", string="Product Category", required=True, index=True,
        ondelete="cascade",
    )
    rate = fields.Float(
        string="Commission (%)", digits=(5, 2), required=True,
        help="Percentage of the untaxed invoiced amount. Zero switches commission "
             "off for this category.",
    )
    company_id = fields.Many2one(
        "res.company", string="Company", required=True, index=True,
        default=lambda self: self.env.company,
    )

    _user_categ_company_uniq = models.Constraint(
        "unique(user_id, categ_id, company_id)",
        "A salesperson already has a rate for this product category in this company.",
    )

    @api.constrains("rate")
    def _check_rate(self):
        for rec in self:
            if rec.rate < 0 or rec.rate > 100:
                raise ValidationError(self.env._("A commission rate must be between 0 and 100 percent."))

    @api.model
    def _get_rate(self, user, categ, company):
        """Rate in percent for ``user`` on a product in ``categ``.

        The category's own rate, else the nearest ancestor's, else the user's
        default. Returns 0.0 when nothing is configured.
        """
        if not user:
            return 0.0
        if categ:
            rates = self.sudo().search([
                ("user_id", "=", user.id),
                ("company_id", "=", company.id),
                ("categ_id", "parent_of", categ.id),
            ])
            if rates:
                by_categ = {r.categ_id: r for r in rates}
                node = categ
                while node:
                    if node in by_categ:
                        return by_categ[node].rate
                    node = node.parent_id
        return user.sudo().drkds_commission_rate or 0.0
