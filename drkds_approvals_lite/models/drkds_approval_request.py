from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

STATES = [
    ("draft", "Draft"),
    ("submitted", "Submitted"),
    ("approved", "Approved"),
    ("refused", "Refused"),
    ("cancelled", "Cancelled"),
]
OPEN_STATES = ("draft", "submitted")


class DrkdsApprovalRequest(models.Model):
    """A request for a yes or a no, decided once by one of the category's approvers.

    Life cycle::

        draft --submit--> submitted --approve--> approved
                              |------refuse---> refused
        draft / submitted --cancel--> cancelled
        refused / cancelled --reset--> draft

    The reference comes from a sequence on first save and never changes.
    Submitting schedules a to-do activity for each approver; the first
    decision closes the request, clears the remaining activities and emails
    the requester. The requester can never decide on their own request, even
    when they are an approver of the category or a manager.
    """

    _name = "drkds.approval.request"
    _description = "Approval Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"
    _rec_names_search = ["name", "title"]
    _check_company_auto = True

    name = fields.Char(
        string="Reference", required=True, copy=False, readonly=True, default="/", index=True
    )
    title = fields.Char(string="Title", required=True, tracking=True)
    category_id = fields.Many2one(
        "drkds.approval.category",
        string="Category",
        required=True,
        tracking=True,
        index=True,
        ondelete="restrict",
        check_company=True,
    )
    requester_id = fields.Many2one(
        "res.users",
        string="Requester",
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
        index=True,
        domain="[('share', '=', False)]",
    )
    date = fields.Date(
        string="Request Date", required=True, default=fields.Date.context_today, tracking=True
    )
    amount = fields.Monetary(string="Amount", currency_field="currency_id", tracking=True)
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    partner_id = fields.Many2one(
        "res.partner", string="Contact", tracking=True, index=True, check_company=True
    )
    description = fields.Html(string="Description", sanitize_style=True)
    state = fields.Selection(
        STATES, default="draft", required=True, tracking=True, index=True, copy=False
    )
    approver_id = fields.Many2one(
        "res.users", string="Decided By", readonly=True, copy=False, tracking=True
    )
    decision_date = fields.Datetime(string="Decision Date", readonly=True, copy=False)
    refusal_reason = fields.Text(string="Refusal Reason", readonly=True, copy=False)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    # Mirrors of the category, so the form can mark fields required and the
    # search view can filter "to approve by me" without a dotted path.
    approver_ids = fields.Many2many(
        related="category_id.approver_ids", string="Approvers", readonly=True
    )
    require_description = fields.Boolean(related="category_id.require_description")
    require_amount = fields.Boolean(related="category_id.require_amount")
    require_partner = fields.Boolean(related="category_id.require_partner")
    can_decide = fields.Boolean(compute="_compute_can_decide")

    _name_uniq = models.Constraint(
        "unique(name)", "A request with this reference already exists."
    )
    _amount_positive = models.Constraint(
        "check(amount >= 0)", "The amount cannot be negative."
    )

    # -- computes ------------------------------------------------------
    @api.depends("state", "requester_id", "category_id.approver_ids")
    @api.depends_context("uid")
    def _compute_can_decide(self):
        """Whether the current user may approve or refuse this request now."""
        user = self.env.user
        is_manager = user.has_group("drkds_approvals_lite.group_approval_manager")
        for request in self:
            request.can_decide = (
                request.state == "submitted"
                and request.requester_id != user
                and (is_manager or user in request.category_id.approver_ids)
            )

    @api.depends("name", "title")
    def _compute_display_name(self):
        for request in self:
            request.display_name = (
                f"{request.name} {request.title}" if request.name != "/" else request.title
            )

    # -- onchange ------------------------------------------------------
    @api.onchange("company_id")
    def _onchange_company_id(self):
        if self.company_id and self.currency_id != self.company_id.currency_id:
            self.currency_id = self.company_id.currency_id

    # -- CRUD ----------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == "/":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("drkds.approval.request") or "/"
                )
        return super().create(vals_list)

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for vals in vals_list:
            vals["name"] = "/"
        return vals_list

    @api.ondelete(at_uninstall=False)
    def _unlink_only_open(self):
        for request in self:
            if request.state not in ("draft", "cancelled"):
                raise UserError(
                    _("Only a draft or cancelled request can be deleted. Cancel it first.")
                )

    # -- guards --------------------------------------------------------
    def _check_submittable(self):
        """Raise if the category's requirements are not met."""
        for request in self:
            category = request.category_id
            missing = []
            if category.require_description and not request.description:
                missing.append(_("a description"))
            if category.require_amount and not request.amount:
                missing.append(_("an amount"))
            if category.require_partner and not request.partner_id:
                missing.append(_("a contact"))
            if missing:
                raise ValidationError(
                    _(
                        "Category %(category)s requires %(missing)s before the request can be submitted.",
                        category=category.name,
                        missing=_(" and ").join(missing),
                    )
                )

    def _check_can_decide(self):
        """Raise unless the current user may decide on every record in self."""
        for request in self:
            if request.state != "submitted":
                raise UserError(
                    _("Only a submitted request can be approved or refused.")
                )
            if request.requester_id == self.env.user:
                raise UserError(_("You cannot decide on your own request."))
            if not request.can_decide:
                raise UserError(
                    _(
                        "Only an approver of category %(category)s may decide on %(name)s.",
                        category=request.category_id.name,
                        name=request.name,
                    )
                )

    def _check_state(self, allowed, action):
        for request in self:
            if request.state not in allowed:
                raise UserError(
                    _(
                        "%(name)s cannot be %(action)s from state %(state)s.",
                        name=request.name,
                        action=action,
                        state=dict(STATES)[request.state],
                    )
                )

    # -- actions -------------------------------------------------------
    def action_submit(self):
        self._check_state(("draft",), _("submitted"))
        self._check_submittable()
        for request in self:
            if not request.category_id.approver_ids:
                raise UserError(
                    _(
                        "Category %s has no approver. Ask an administrator to add one.",
                        request.category_id.name,
                    )
                )
        self.write({"state": "submitted"})
        self._schedule_approver_activities()

    def action_approve(self):
        self._check_can_decide()
        self.write(
            {
                "state": "approved",
                "approver_id": self.env.uid,
                "decision_date": fields.Datetime.now(),
                "refusal_reason": False,
            }
        )
        self._close_approver_activities()
        self.message_post_with_source(
            "drkds_approvals_lite.mail_template_approval_approved",
            subtype_xmlid="mail.mt_comment",
        )

    def action_refuse(self, reason):
        """Refuse with a reason. The form goes through the wizard, which
        collects the reason; code may call this directly."""
        if not reason or not reason.strip():
            raise ValidationError(_("A refusal needs a reason."))
        self._check_can_decide()
        self.write(
            {
                "state": "refused",
                "approver_id": self.env.uid,
                "decision_date": fields.Datetime.now(),
                "refusal_reason": reason.strip(),
            }
        )
        self._close_approver_activities()
        self.message_post_with_source(
            "drkds_approvals_lite.mail_template_approval_refused",
            subtype_xmlid="mail.mt_comment",
        )

    def action_open_refuse_wizard(self):
        self.ensure_one()
        self._check_can_decide()
        return {
            "type": "ir.actions.act_window",
            "name": _("Refuse Request"),
            "res_model": "drkds.approval.refuse.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    def action_cancel(self):
        self._check_state(OPEN_STATES, _("cancelled"))
        for request in self:
            if (
                request.requester_id != self.env.user
                and not self.env.user.has_group("drkds_approvals_lite.group_approval_manager")
            ):
                raise UserError(
                    _("Only the requester or an approval administrator can cancel %s.", request.name)
                )
        self.write({"state": "cancelled"})
        self._close_approver_activities()

    def action_reset_to_draft(self):
        self._check_state(("refused", "cancelled"), _("reset to draft"))
        self.write(
            {
                "state": "draft",
                "approver_id": False,
                "decision_date": False,
                "refusal_reason": False,
            }
        )

    # -- activities ----------------------------------------------------
    def _schedule_approver_activities(self):
        for request in self:
            for approver in request.category_id.approver_ids:
                request.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=approver.id,
                    summary=_("Decide on %s", request.name),
                    note=_(
                        "%(requester)s asks for a decision on %(title)s.",
                        requester=request.requester_id.name,
                        title=request.title,
                    ),
                )

    def _close_approver_activities(self):
        """Drop the to-dos still open for the other approvers.

        They are unlinked rather than marked done: a done activity would
        read as if every approver had acted, which is not what happened.
        Runs as superuser because mail lets a user delete only the
        activities they created or own, and the deciding approver is
        neither for the to-dos of the other approvers.
        """
        self.sudo().activity_unlink(["mail.mail_activity_data_todo"])
