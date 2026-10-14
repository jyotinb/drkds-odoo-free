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
        string="Commission (%)", digits=(5, 2), required=True, aggregator=None,
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
        """Rate in percent for ``user`` on a product in ``categ``, sold by ``company``.

        The category's own rate, else the nearest ancestor's, else the user's
        default. Rates of the company's parents apply to a branch; for the same
        category the nearest company wins. Returns 0.0 when nothing is configured.
        """
        if not user:
            return 0.0
        if categ:
            companies = company.parent_ids  # root first, ``company`` last
            rates = self.sudo().search([
                ("user_id", "=", user.id),
                ("company_id", "in", companies.ids),
                ("categ_id", "parent_of", categ.id),
            ])
            if rates:
                depth = {c: i for i, c in enumerate(companies)}
                by_categ = {}
                for rate in rates:
                    best = by_categ.get(rate.categ_id)
                    if not best or depth[rate.company_id] > depth[best.company_id]:
                        by_categ[rate.categ_id] = rate
                node = categ
                while node:
                    if node in by_categ:
                        return by_categ[node].rate
                    node = node.parent_id
        return user.sudo().drkds_commission_rate or 0.0
