from odoo import api, fields, models


class StockMove(models.Model):
    """Link a stock move back to the material request line that caused it."""

    _inherit = "stock.move"

    drkds_request_line_id = fields.Many2one(
        "drkds.material.request.line", string="Material Request Line",
        ondelete="set null", index="btree_not_null", copy=False,
    )

    def _action_done(self, cancel_backorder=False):
        moves = super()._action_done(cancel_backorder=cancel_backorder)
        requests = moves.drkds_request_line_id.request_id
        if requests:
            requests._check_fulfilment()
        return moves
