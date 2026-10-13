from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    drkds_commission_line_ids = fields.One2many(
        "drkds.commission.line", "move_id", string="Commission Lines", readonly=True,
    )
    drkds_commission_count = fields.Integer(
        string="Commission Line Count", compute="_compute_drkds_commission_count",
    )

    @api.depends("drkds_commission_line_ids")
    def _compute_drkds_commission_count(self):
        for move in self:
            move.drkds_commission_count = len(move.drkds_commission_line_ids.sudo())

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        self.env["drkds.commission.line"]._generate_for_moves(posted)
        return posted

    def button_draft(self):
        """Resetting to draft (which cancel goes through) withdraws the commission.

        Paid lines are not silently dropped: the money has left, so the manager
        must first mark them unpaid, consciously.
        """
        lines = self.env["drkds.commission.line"].sudo().search([("move_id", "in", self.ids)])
        paid = lines.filtered(lambda l: l.state == "paid")
        if paid:
            raise UserError(self.env._(
                "%s has commission lines already marked as paid. Mark them unpaid "
                "before resetting or cancelling the invoice.",
                ", ".join(paid.mapped("move_id.display_name")),
            ))
        res = super().button_draft()
        lines.unlink()
        return res

    def action_view_drkds_commission_lines(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "drkds_commission_lite.action_drkds_commission_line"
        )
        action["domain"] = [("move_id", "=", self.id)]
        action["context"] = {"search_default_group_user": 0}
        return action
