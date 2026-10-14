from odoo import api, fields, models
from odoo.exceptions import UserError

# Whoever may read commission lines (see ir.model.access.csv). Anyone else opening
# an invoice (a purchase user, a read-only accountant) must not get these fields.
_COMMISSION_READERS = "sales_team.group_sale_salesman,account.group_account_invoice"


class AccountMove(models.Model):
    _inherit = "account.move"

    drkds_commission_line_ids = fields.One2many(
        "drkds.commission.line", "move_id", string="Commission Lines", readonly=True,
        groups=_COMMISSION_READERS,
    )
    # Named after this module's own model: drkds_sales_commission, which can be
    # installed alongside, adds a drkds_commission_count of its own to invoices.
    drkds_commission_line_count = fields.Integer(
        string="Commission Line Count", compute="_compute_drkds_commission_line_count",
        groups=_COMMISSION_READERS,
    )

    @api.depends("drkds_commission_line_ids")
    def _compute_drkds_commission_line_count(self):
        for move in self:
            move.drkds_commission_line_count = len(move.drkds_commission_line_ids.sudo())

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        self.env["drkds.commission.line"]._generate_for_moves(posted)
        return posted

    def button_draft(self):
        """Resetting to draft (which cancel goes through) withdraws the commission.

        Unpaid lines go. Paid lines stay as the record of money paid out, and
        what they paid is taken back with negative unpaid lines.
        """
        res = super().button_draft()
        self.env["drkds.commission.line"]._generate_for_moves(self)
        return res

    def write(self, vals):
        if "invoice_user_id" not in vals:
            return super().write(vals)
        before = {move: move.invoice_user_id for move in self}
        res = super().write(vals)
        # The salesperson of a posted invoice can still be corrected.
        changed = self.filtered(lambda m: m.state == "posted" and m.invoice_user_id != before[m])
        if changed:
            self.env["drkds.commission.line"]._generate_for_moves(changed)
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_except_paid_commission(self):
        paid = self.env["drkds.commission.line"].sudo().search(
            [("move_id", "in", self.ids), ("state", "=", "paid")],
        )
        if paid:
            raise UserError(self.env._(
                "Commission has already been paid out on %s. Cancel the invoice instead of "
                "deleting it, so that the payment stays on record.",
                ", ".join(paid.move_id.mapped("display_name")),
            ))

    def action_view_drkds_commission_lines(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "drkds_commission_lite.action_drkds_commission_line"
        )
        action["domain"] = [("move_id", "=", self.id)]
        action["context"] = {"search_default_group_user": 0}
        return action
