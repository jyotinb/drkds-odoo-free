from odoo import api, fields, models
from odoo.exceptions import UserError


class QualityCheck(models.Model):
    """One inspection of one stock move against one control point."""

    _name = "drkds.quality.check"
    _description = "Quality Check"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"
    _check_company_auto = True

    name = fields.Char(
        string="Reference", required=True, copy=False, readonly=True,
        default=lambda self: self.env._("New"),
    )
    company_id = fields.Many2one(
        "res.company", string="Company", required=True, index=True,
        default=lambda self: self.env.company,
    )
    point_id = fields.Many2one(
        "drkds.quality.point", string="Control Point", required=True,
        ondelete="cascade", check_company=True, index=True, tracking=True,
    )
    check_type = fields.Selection(related="point_id.check_type")
    blocking = fields.Boolean(related="point_id.blocking")
    instructions = fields.Html(related="point_id.instructions")
    norm_min = fields.Float(related="point_id.norm_min")
    norm_max = fields.Float(related="point_id.norm_max")
    measure_unit = fields.Char(related="point_id.measure_unit")
    picking_id = fields.Many2one(
        "stock.picking", string="Transfer", ondelete="cascade",
        check_company=True, index=True,
    )
    picking_type_id = fields.Many2one(related="picking_id.picking_type_id", store=True)
    move_id = fields.Many2one(
        "stock.move", string="Stock Move", ondelete="cascade",
        check_company=True, index=True,
    )
    product_id = fields.Many2one(
        "product.product", string="Product", required=True,
        check_company=True, index=True,
    )
    lot_id = fields.Many2one(
        "stock.lot", string="Lot / Serial", check_company=True,
        domain="[('product_id', '=', product_id)]",
    )
    state = fields.Selection(
        [("todo", "To Do"), ("pass", "Passed"), ("fail", "Failed")],
        string="Status", default="todo", required=True, copy=False,
        index=True, tracking=True,
    )
    measure = fields.Float(string="Measure", digits="Product Unit", tracking=True)
    note = fields.Text(string="Note")
    user_id = fields.Many2one(
        "res.users", string="Checked By", readonly=True, copy=False,
    )
    date = fields.Datetime(string="Checked On", readonly=True, copy=False)
    partner_id = fields.Many2one(related="picking_id.partner_id", string="Contact")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", self.env._("New")) == self.env._("New"):
                company_id = vals.get("company_id") or self.env.company.id
                vals["name"] = self.env["ir.sequence"].with_company(
                    company_id
                ).next_by_code("drkds.quality.check") or self.env._("New")
        return super().create(vals_list)

    @api.onchange("move_id")
    def _onchange_move_id(self):
        for check in self:
            if check.move_id:
                check.product_id = check.move_id.product_id
                check.picking_id = check.move_id.picking_id

    # -- decisions -----------------------------------------------------
    def _set_result(self, state):
        self.write({
            "state": state,
            "user_id": self.env.user.id,
            "date": fields.Datetime.now(),
        })
        return True

    def action_pass(self):
        if any(c.check_type == "measure" for c in self):
            raise UserError(self.env._(
                "A measured check is decided by its measure. Enter the value "
                "and record it."
            ))
        return self._set_result("pass")

    def action_fail(self):
        if any(c.check_type == "measure" for c in self):
            raise UserError(self.env._(
                "A measured check is decided by its measure. Enter the value "
                "and record it."
            ))
        return self._set_result("fail")

    def action_measure(self):
        """Decide a measured check from its value and the point's range."""
        for check in self:
            if check.check_type != "measure":
                raise UserError(self.env._(
                    "%s is a pass/fail check; use the Pass or Fail button.",
                    check.name,
                ))
            check._set_result(
                "pass" if check.point_id._measure_in_range(check.measure) else "fail"
            )
        return True

    def action_reset_todo(self):
        return self.write({"state": "todo", "user_id": False, "date": False})

    # -- creation from moves -------------------------------------------
    @api.model
    def _create_for_moves(self, moves):
        """Raise one check per (point, move) pair that matches and does not
        exist yet. Returns the checks created."""
        moves = moves.filtered(
            lambda m: m.picking_id and m.state not in ("draft", "cancel", "done")
        )
        if not moves:
            return self.browse()
        points = self.env["drkds.quality.point"].search(
            [("company_id", "in", moves.company_id.ids)]
        )
        if not points:
            return self.browse()
        existing = {
            (row["move_id"][0], row["point_id"][0])
            for row in self.search_read(
                [("move_id", "in", moves.ids), ("point_id", "in", points.ids)],
                ["move_id", "point_id"],
            )
        }
        vals_list = []
        for move in moves:
            for point in points:
                if (move.id, point.id) in existing or not point._matches_move(move):
                    continue
                vals_list.append({
                    "point_id": point.id,
                    "move_id": move.id,
                    "picking_id": move.picking_id.id,
                    "product_id": move.product_id.id,
                    "company_id": move.company_id.id,
                })
        return self.create(vals_list)
