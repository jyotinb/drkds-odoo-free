from odoo import fields, models

from .drkds_approval_request import _approval_user_domain


class DrkdsApprovalCategory(models.Model):
    """A kind of request, with the people allowed to decide on it.

    The category decides two things: who may approve or refuse, and what a
    request must carry before it can be submitted (a description, an amount,
    a contact). Those checks run on submit, not on save, so a draft can be
    filled in over several sittings.

    Changing the approvers reaches the requests already waiting: a removed
    approver's to-do is dropped and a new approver gets one, so the to-do
    list always matches who can decide.
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
        domain=_approval_user_domain,
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

    def write(self, vals):
        if "approver_ids" not in vals:
            return super().write(vals)
        previous = {category.id: category.approver_ids for category in self}
        result = super().write(vals)
        for category in self:
            before = previous[category.id]
            removed = before - category.approver_ids
            added = category.approver_ids - before
            if removed or added:
                category._update_waiting_request_activities(added, removed)
        return result

    def _update_waiting_request_activities(self, added, removed):
        """Move the to-dos of this category's submitted requests from the
        `removed` approvers to the `added` ones.

        A system consequence of editing the category, so it runs as
        superuser: the administrator editing it may own none of the to-dos.
        """
        self.ensure_one()
        waiting = self.env["drkds.approval.request"].sudo().search(
            [("category_id", "=", self.id), ("state", "=", "submitted")]
        )
        if not waiting:
            return
        if removed:
            waiting._close_approver_activities(users=removed)
        if added:
            waiting._schedule_approver_activities(users=added)

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
