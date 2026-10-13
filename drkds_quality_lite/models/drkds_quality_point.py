from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class QualityPoint(models.Model):
    """What must be checked, on which goods, on which kind of transfer.

    A point is the rule; a check is one application of the rule to one stock
    move. A point names either a product or a product category (or both, in
    which case the product wins and the category is only a fallback) and the
    operation types it applies to. An empty operation-type list means every
    operation type.
    """

    _name = "drkds.quality.point"
    _description = "Quality Control Point"
    _order = "sequence, id"
    _check_company_auto = True

    name = fields.Char(string="Title", required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", string="Company", required=True, index=True,
        default=lambda self: self.env.company,
    )
    product_id = fields.Many2one(
        "product.product", string="Product", check_company=True,
        ondelete="cascade",
        help="Check every move of this product. Leave empty to match on the "
             "product category instead.",
    )
    product_category_id = fields.Many2one(
        "product.category", string="Product Category", ondelete="cascade",
        help="Check every move of a product in this category or one of its "
             "sub-categories. Ignored when a product is set.",
    )
    picking_type_ids = fields.Many2many(
        "stock.picking.type", "drkds_quality_point_picking_type_rel",
        "point_id", "picking_type_id", string="Operation Types",
        check_company=True,
        help="Transfers of these operation types raise this check. Leave "
             "empty for every operation type of the company.",
    )
    instructions = fields.Html(
        string="Instructions", translate=True, sanitize=True,
        help="Shown to the inspector on the check.",
    )
    check_type = fields.Selection(
        [("pass_fail", "Pass / Fail"), ("measure", "Measure")],
        string="Type", required=True, default="pass_fail",
    )
    norm_min = fields.Float(string="Minimum", digits="Product Unit")
    norm_max = fields.Float(string="Maximum", digits="Product Unit")
    measure_unit = fields.Char(string="Unit", help="Free text, for example mm, kg or pH.")
    blocking = fields.Boolean(
        string="Blocks Validation", default=True,
        help="When set, the transfer cannot be validated while a check of "
             "this point is still to do or has failed. Unset it to record the "
             "result without holding up the goods.",
    )
    check_ids = fields.One2many("drkds.quality.check", "point_id", string="Checks")
    check_count = fields.Integer(compute="_compute_check_count")

    _name_company_uniq = models.Constraint(
        "unique(name, company_id)",
        "A control point with this title already exists in this company.",
    )

    @api.depends("check_ids")
    def _compute_check_count(self):
        counts = dict(self.env["drkds.quality.check"]._read_group(
            [("point_id", "in", self.ids)], ["point_id"], ["__count"],
        ))
        for point in self:
            point.check_count = counts.get(point, 0)

    # ``name`` is required, so listing it makes the constraint run on every
    # create, including one that sets neither product nor category.
    @api.constrains("name", "product_id", "product_category_id")
    def _check_target(self):
        for point in self:
            if not point.product_id and not point.product_category_id:
                raise ValidationError(
                    self.env._("A control point needs a product or a product category.")
                )

    @api.constrains("check_type", "norm_min", "norm_max")
    def _check_norms(self):
        for point in self:
            if point.check_type == "measure" and point.norm_min > point.norm_max:
                raise ValidationError(
                    self.env._("The minimum of a measured check cannot exceed its maximum.")
                )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_with_checks(self):
        """The checks a point raised are the inspection record of past
        transfers; deleting the point must not take them with it."""
        used = self.sudo().filtered("check_ids")
        if used:
            raise UserError(self.env._(
                "%(points)s already raised quality checks and cannot be "
                "deleted. Archive it instead: it stops raising checks and "
                "its history is kept.",
                points=", ".join(used.mapped("name")),
            ))

    def _matches_move(self, move):
        """Whether this point applies to ``move``.

        Product wins over category; an empty operation-type list matches any.
        """
        self.ensure_one()
        if self.company_id != move.company_id:
            return False
        if self.picking_type_ids and move.picking_type_id not in self.picking_type_ids:
            return False
        if self.product_id:
            return move.product_id == self.product_id
        categ = move.product_id.categ_id
        return bool(categ) and (
            categ == self.product_category_id
            or categ.parent_path.startswith(self.product_category_id.parent_path)
        )

    def _measure_in_range(self, value):
        self.ensure_one()
        return self.norm_min <= value <= self.norm_max

    def action_view_checks(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "drkds_quality_lite.action_drkds_quality_check"
        )
        action["domain"] = [("point_id", "=", self.id)]
        action["context"] = {"default_point_id": self.id, "search_default_todo": 1}
        return action
