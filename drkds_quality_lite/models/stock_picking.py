from odoo import api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # Inventory users only. Buyers and salespeople open transfers through
    # purchase_stock and sale_stock without any right on quality checks; a
    # field they cannot read in the transfer form makes the whole form fail
    # to load for them.
    drkds_quality_check_ids = fields.One2many(
        "drkds.quality.check", "picking_id", string="Quality Checks",
        groups="stock.group_stock_user",
    )
    drkds_quality_check_count = fields.Integer(
        string="Quality Check Count", compute="_compute_drkds_quality_counts",
        groups="stock.group_stock_user",
    )
    drkds_quality_open_count = fields.Integer(
        string="Open Quality Checks", compute="_compute_drkds_quality_counts",
        groups="stock.group_stock_user",
        help="Checks still to do or failed.",
    )

    @api.depends("drkds_quality_check_ids.state")
    def _compute_drkds_quality_counts(self):
        for picking in self:
            checks = picking.drkds_quality_check_ids
            picking.drkds_quality_check_count = len(checks)
            picking.drkds_quality_open_count = len(
                checks.filtered(lambda c: c.state != "pass")
            )

    def action_view_drkds_quality_checks(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "drkds_quality_lite.action_drkds_quality_check"
        )
        action["domain"] = [("picking_id", "=", self.id)]
        action["context"] = {
            "default_picking_id": self.id,
            "default_company_id": self.company_id.id,
        }
        if len(self.drkds_quality_check_ids) == 1:
            action["views"] = [(False, "form")]
            action["res_id"] = self.drkds_quality_check_ids.id
        return action

    def _drkds_quality_moves_to_process(self):
        """The moves that validating these transfers will actually process.

        Stock validates a move only when it is picked and has a quantity
        (``stock.move._action_done``); any other move goes to the backorder
        or is cancelled, and its checks go with it. Before the pre-validation
        hook has run, a transfer where nothing is ticked as picked counts as
        all picked, which is what that hook then does.
        """
        moves = self.env["stock.move"]
        for picking in self:
            open_moves = picking.move_ids.filtered(
                lambda m: m.state not in ("done", "cancel")
            )
            nothing_picked = not any(open_moves.mapped("picked"))
            moves |= open_moves.filtered(
                lambda m: (m.picked or nothing_picked) and (
                    m.is_inventory or m.product_uom.compare(m.quantity, 0) > 0
                )
            )
        return moves

    def _drkds_quality_blocking_checks(self):
        """Blocking checks, not passed, that stand in the way of validating
        these transfers now: those of the moves being processed, and those
        entered on the transfer without a move. Read as superuser: the rule
        holds whoever validates."""
        moves = self._drkds_quality_moves_to_process()
        return self.sudo().drkds_quality_check_ids.filtered(
            lambda c: c.blocking and c.state != "pass"
            and (not c.move_id or c.move_id in moves)
        )

    def _drkds_quality_gate(self):
        """Refuse to go further while a blocking check is open or failed."""
        for picking in self:
            open_checks = picking._drkds_quality_blocking_checks()
            if open_checks:
                states = dict(open_checks._fields["state"]._description_selection(self.env))
                raise UserError(self.env._(
                    "%(picking)s cannot be validated: the following quality "
                    "checks must pass first.\n%(checks)s",
                    picking=picking.name,
                    checks="\n".join(
                        "- %s: %s (%s)" % (c.name, c.point_id.name, states[c.state])
                        for c in open_checks
                    ),
                ))

    def _drkds_quality_draft_gate(self):
        """Refuse to validate a draft transfer that blocking points apply to.

        Validating from draft confirms the transfer inside the same request,
        which raises its checks; the validation is then bound to be refused,
        and a refused request is rolled back, confirmation and checks with
        it, while the message still named checks that no longer exist. So
        refuse before confirming, and say what to do instead.
        """
        Point = self.env["drkds.quality.point"].sudo()
        for picking in self:
            points = Point.search([
                ("company_id", "=", picking.company_id.id), ("blocking", "=", True),
            ])
            hits = [
                (point, move)
                for move in picking.move_ids.filtered(lambda m: m.state == "draft")
                for point in points
                if point._matches_move(move)
            ]
            if hits:
                raise UserError(self.env._(
                    "%(picking)s has quality checks to pass before it can be "
                    "validated:\n%(checks)s\nPress Mark as To Do to raise the "
                    "checks, record their results, then validate.",
                    picking=picking.name,
                    checks="\n".join(
                        "- %s: %s" % (point.name, move.product_id.display_name)
                        for point, move in hits
                    ),
                ))

    def button_validate(self):
        # Fail fast, before any pre-validation wizard is shown. _action_done
        # repeats the gate for every other path to done.
        self.filtered(lambda p: p.state == "draft")._drkds_quality_draft_gate()
        self.filtered(
            lambda p: p.state not in ("draft", "done", "cancel")
        )._drkds_quality_gate()
        return super().button_validate()

    def _action_done(self):
        # Every path to done passes here, wizards included.
        self._drkds_quality_gate()
        return super()._action_done()
