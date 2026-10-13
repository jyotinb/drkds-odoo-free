from odoo import fields, models


class DrkdsApprovalRefuseWizard(models.TransientModel):
    """Collects the reason a request is refused. The reason is mandatory."""

    _name = "drkds.approval.refuse.wizard"
    _description = "Refuse Approval Request"

    request_id = fields.Many2one(
        "drkds.approval.request", string="Request", required=True, readonly=True
    )
    reason = fields.Text(string="Reason", required=True)

    def action_refuse(self):
        self.ensure_one()
        self.request_id.action_refuse(self.reason)
        return {"type": "ir.actions.act_window_close"}
