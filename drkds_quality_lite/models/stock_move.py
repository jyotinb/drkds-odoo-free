from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _action_confirm(self, merge=True, merge_into=False, create_proc=True):
        """Raise the quality checks once a move is confirmed.

        Hooked here rather than on the picking so that a move added to an
        already confirmed transfer is checked too. ``super`` may merge moves,
        so the checks are raised on what it returns.
        """
        moves = super()._action_confirm(
            merge=merge, merge_into=merge_into, create_proc=create_proc
        )
        self.env["drkds.quality.check"]._create_for_moves(moves)
        return moves

    def _action_cancel(self):
        """A cancelled move has nothing left to inspect: drop its open checks.
        Decided checks stay as history."""
        res = super()._action_cancel()
        cancelled = self.filtered(lambda m: m.state == "cancel")
        if cancelled:
            self.env["drkds.quality.check"].sudo().search([
                ("move_id", "in", cancelled.ids), ("state", "=", "todo"),
            ]).unlink()
        return res
