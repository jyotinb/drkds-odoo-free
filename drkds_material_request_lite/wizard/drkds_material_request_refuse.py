from odoo import _, fields, models
from odoo.exceptions import UserError


class DrkdsMaterialRequestRefuse(models.TransientModel):
    """Captures the reason an approver refuses a material request.

    The reason exists so the requester learns something from the refusal. It
    is therefore mandatory, both here and on the model method behind it.
    """

    _name = "drkds.material.request.refuse"
    _description = "Refuse Material Request"

    request_id = fields.Many2one(
        "drkds.material.request", string="Request", required=True,
        ondelete="cascade",
    )
    reason = fields.Text(string="Refusal Reason", required=True)

    def action_confirm(self):
        self.ensure_one()
        if not (self.reason or "").strip():
            raise UserError(_("A refusal must say why the request is turned down."))
        self.request_id.action_refuse_with_reason(self.reason)
        return {"type": "ir.actions.act_window_close"}
