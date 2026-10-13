from odoo import api, fields, models


class DrkdsApprovalCategory(models.Model):
    """A kind of request, with the people allowed to decide on it.

    The category decides two things: who may approve or refuse, and what a
    request must carry before it can be submitted (a description, an amount,
    a contact). Those checks run on submit, not on save, so a draft can be
    filled in over several sittings.
    """

    _name = "drkds.approval.category"
    _description = "Approval Category"
    _order = "sequence, id"
    _check_company_auto = True

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text(translate=True)
    approver_ids = fields.Many2many(
        "res.users",
        "drkds_approval_category_approver_rel",
        "category_id",
        "user_id",
        string="Approvers",
        domain="[('share', '=', False)]",
        help="Any one of these users may approve or refuse a request of this category.",
    )
    require_description = fields.Boolean(
        string="Description Required", default=True,
        help="A request cannot be submitted without a description.",
    )
    require_amount = fields.Boolean(
        string="Amount Required",
        help="A request cannot be submitted with a zero or empty amount.",
    )
    require_partner = fields.Boolean(
        string="Contact Required",
        help="A request cannot be submitted without a contact.",
    )
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company, index=True
    )
    request_count = fields.Integer(compute="_compute_request_count")

    def _compute_request_count(self):
        groups = self.env["drkds.approval.request"]._read_group(
            [("category_id", "in", self.ids)], ["category_id"], ["__count"]
        )
        counts = {category.id: count for category, count in groups}
        for category in self:
            category.request_count = counts.get(category.id, 0)

    def action_view_requests(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "drkds_approvals_lite.action_drkds_approval_request"
        )
        action["domain"] = [("category_id", "=", self.id)]
        action["context"] = {"default_category_id": self.id, "search_default_open": 1}
        return action
