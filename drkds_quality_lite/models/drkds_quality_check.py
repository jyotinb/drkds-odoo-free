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
    # restrict: a check is the inspection record of a transfer; deleting its
    # point must not delete it (the point refuses deletion, see its ondelete).
    point_id = fields.Many2one(
        "drkds.quality.point", string="Control Point", required=True,
        ondelete="restrict", check_company=True, index=True, tracking=True,
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
        compute="_compute_picking_id", store=True, readonly=False,
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

    @api.depends("move_id.picking_id")
    def _compute_picking_id(self):
        """A check follows its move.

        Stock moves the rest of a partly validated move, and the moves left
        untouched, to a backorder or a split-off transfer by rewriting the
        move's transfer. The check has to go along: otherwise the backorder
        carries no check and validates uninspected, while the original keeps
        a check for goods it no longer holds. A check entered by hand without
        a move keeps the transfer it was given.
        """
        for check in self:
            check.picking_id = check.move_id.picking_id if check.move_id else check.picking_id

    @api.onchange("move_id")
    def _onchange_move_id(self):
        for check in self:
            if check.move_id:
                check.product_id = check.move_id.product_id

    # -- decisions -----------------------------------------------------
    def _check_still_todo(self):
        """A decision is taken once. A second Pass or Fail, from a form left
        open by another inspector for instance, must not silently replace
        the first; changing a result goes through Reset to To Do, which the
        chatter records."""
        states = dict(self._fields["state"]._description_selection(self.env))
        for check in self:
            if check.state != "todo":
                raise UserError(self.env._(
                    "%(check)s is already decided (%(state)s by %(user)s). "
                    "Reset it to To Do to change the result.",
                    check=check.name, state=states[check.state],
                    user=check.user_id.name or "-",
                ))

    def _set_result(self, state):
        self.write({
            "state": state,
            "user_id": self.env.user.id,
            "date": fields.Datetime.now(),
        })
        return True

    def action_pass(self):
        self._check_still_todo()
        if any(c.check_type == "measure" for c in self):
            raise UserError(self.env._(
                "A measured check is decided by its measure. Enter the value "
                "and record it."
            ))
        return self._set_result("pass")

    def action_fail(self):
        self._check_still_todo()
        if any(c.check_type == "measure" for c in self):
            raise UserError(self.env._(
                "A measured check is decided by its measure. Enter the value "
                "and record it."
            ))
        return self._set_result("fail")

    def action_measure(self):
        """Decide a measured check from its value and the point's range."""
        self._check_still_todo()
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
        exist yet. Returns the checks created, in the caller's environment.

        Runs as superuser: raising checks is a consequence of confirming a
        move, not a decision of whoever confirmed it, who may be a buyer or a
        salesperson with no right on quality records at all. The company is
        matched by the point itself (``_matches_move``), not through the
        current user's record rules, and the confirming user is not made a
        follower of checks they may be unable to open.
        """
        Check = self.sudo().with_context(mail_create_nosubscribe=True)
        moves = moves.sudo().filtered(
            lambda m: m.picking_id and m.state not in ("draft", "cancel", "done")
        )
        if not moves:
            return self.browse()
        points = self.env["drkds.quality.point"].sudo().search(
            [("company_id", "in", moves.company_id.ids)]
        )
        if not points:
            return self.browse()
        existing = {
            (row["move_id"][0], row["point_id"][0])
            for row in Check.search_read(
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
        return Check.create(vals_list).with_env(self.env)
