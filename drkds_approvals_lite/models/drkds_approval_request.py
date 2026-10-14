from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import is_html_empty

STATES = [
    ("draft", "Draft"),
    ("submitted", "Submitted"),
    ("approved", "Approved"),
    ("refused", "Refused"),
    ("cancelled", "Cancelled"),
]
OPEN_STATES = ("draft", "submitted")

# Set only by the Submit, Approve, Refuse, Cancel and Reset to Draft buttons.
WORKFLOW_FIELDS = frozenset({"state", "approver_id", "decision_date", "refusal_reason"})
# What the approver decides on. Frozen once the request leaves draft, so an
# approved amount stays the amount that was approved.
CONTENT_FIELDS = frozenset({
    "title", "category_id", "requester_id", "date", "amount", "currency_id",
    "partner_id", "description", "company_id",
})
APPROVAL_USER_GROUP = "drkds_approvals_lite.group_approval_user"
APPROVAL_MANAGER_GROUP = "drkds_approvals_lite.group_approval_manager"


def _approval_user_domain(model):
    """Picker domain for requesters and approvers: internal users holding the
    approvals access, the only people who can open a request.

    Returned as a string on purpose: Odoo applies a list domain of a
    relational field on the server too (reading an x2many filters its
    values), which would hide an approver who later lost the group instead
    of showing them. A string domain only guides the picker.
    """
    group = model.env.ref(APPROVAL_USER_GROUP, raise_if_not_found=False)
    if not group:
        return "[('share', '=', False)]"
    return f"[('share', '=', False), ('all_group_ids', 'in', [{group.id}])]"


class DrkdsApprovalRequest(models.Model):
    """A request for a yes or a no, decided once by one of the category's approvers.

    Life cycle::

        draft --submit--> submitted --approve--> approved
                              |------refuse---> refused
        draft / submitted --cancel--> cancelled
        refused / cancelled --reset--> draft

    The reference comes from a sequence on first save and never changes.
    Submitting schedules a to-do activity for each approver who can decide;
    the first decision closes the request, clears the remaining activities
    and mails the requester. Neither the requester nor whoever raised the
    request on their behalf can decide on it, even as an approver of the
    category or a manager.

    State and decision fields change only through the buttons, and what was
    asked for (title, amount, category...) only while the request is a draft:
    ``write`` refuses anything else from a non-superuser environment, and the
    buttons apply their change through ``sudo()`` after their own checks.
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
        domain=_approval_user_domain,
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
    # group_expand: the board grouped by state shows every state, in the
    # order of the workflow, not sorted by name (Approved before Draft).
    state = fields.Selection(
        STATES, default="draft", required=True, tracking=True, index=True, copy=False,
        group_expand=True,
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
    can_manage = fields.Boolean(
        compute="_compute_can_manage",
        help="Whether the current user may submit, cancel or reset this request.",
    )

    _name_uniq = models.Constraint(
        "unique(name)", "A request with this reference already exists."
    )
    _amount_positive = models.Constraint(
        "check(amount >= 0)", "The amount cannot be negative."
    )

    # -- computes ------------------------------------------------------
    @api.depends("state", "requester_id", "create_uid", "category_id.approver_ids")
    @api.depends_context("uid")
    def _compute_can_decide(self):
        """Whether the current user may approve or refuse this request now."""
        user = self.env.user
        is_manager = user.has_group(APPROVAL_MANAGER_GROUP)
        for request in self:
            request.can_decide = (
                request.state == "submitted"
                and not request._is_raised_by(user)
                and (is_manager or user in request.category_id.approver_ids)
            )

    @api.depends("requester_id", "create_uid")
    @api.depends_context("uid")
    def _compute_can_manage(self):
        """Submit, Cancel and Reset to Draft belong to whoever asked for the
        request and to approval administrators; an unsaved request is the
        current user's own."""
        user = self.env.user
        is_manager = user.has_group(APPROVAL_MANAGER_GROUP)
        for request in self:
            request.can_manage = (
                is_manager or not request._origin.id or request._is_raised_by(user)
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
        requests = super().create(vals_list)
        if not self.env.su:
            # Checked on the records, not on vals_list, so that a
            # default_state=... in the context is caught as well.
            requests._check_created_as_draft()
        return requests

    def write(self, vals):
        if not self.env.su:
            self._check_writable(vals)
        return super().write(vals)

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
    def _check_created_as_draft(self):
        if any(
            request.state != "draft"
            or request.approver_id
            or request.decision_date
            or request.refusal_reason
            for request in self
        ):
            raise UserError(
                _("A new request starts as a draft. Submit it, and an approver approves or refuses it.")
            )

    def _check_writable(self, vals):
        """Keep the decision trail honest against direct writes (an RPC
        client does not go through the buttons or the readonly form)."""
        if "name" in vals:
            raise UserError(_("The reference of a request is allocated once and never changes."))
        if WORKFLOW_FIELDS.intersection(vals):
            raise UserError(
                _(
                    "The state and the decision of a request change only through its "
                    "Submit, Approve, Refuse, Cancel and Reset to Draft buttons."
                )
            )
        if CONTENT_FIELDS.intersection(vals):
            locked = self.filtered(lambda request: request.state != "draft")
            if locked:
                raise UserError(
                    _(
                        "%(names)s can no longer be changed: only a draft request can be "
                        "edited. Cancel it or have it refused, reset it to draft, then edit it.",
                        names=", ".join(locked.mapped("name")),
                    )
                )

    def _is_raised_by(self, user):
        """Whether `user` asked for this request: they are its requester, or
        they raised it on the requester's behalf. Such a user never decides."""
        self.ensure_one()
        return user in (self.requester_id | self.create_uid)

    def _check_raised_by_or_manager(self, action):
        for request in self:
            if not request.can_manage:
                raise UserError(
                    _(
                        "Only the requester, whoever raised the request for them, or an "
                        "approval administrator can %(action)s %(name)s.",
                        action=action,
                        name=request.name,
                    )
                )

    def _check_submittable(self):
        """Raise if the category's requirements are not met, or if no
        approver of the category could decide on the request."""
        for request in self:
            category = request.category_id
            missing = []
            if category.require_description and is_html_empty(request.description):
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
            if not category.approver_ids:
                raise UserError(
                    _(
                        "Category %s has no approver. Ask an administrator to add one.",
                        category.name,
                    )
                )
            if not request._get_deciders():
                raise UserError(
                    _(
                        "Nobody can decide on %(name)s. An approver of category %(category)s "
                        "must not be the requester or whoever raised the request, and needs "
                        "access to Approval Requests and to company %(company)s. "
                        "Ask an administrator to add one.",
                        name=request.name,
                        category=category.name,
                        company=request.company_id.name,
                    )
                )

    def _check_can_decide(self):
        """Raise unless the current user may decide on every record in self."""
        for request in self:
            if request.state != "submitted":
                raise UserError(
                    _("Only a submitted request can be approved or refused.")
                )
            if request._is_raised_by(self.env.user):
                raise UserError(
                    _("You cannot decide on a request you asked for or raised for someone else.")
                )
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

    def _get_deciders(self):
        """The category's approvers who can actually act on this request:
        not the requester or whoever raised it, holding the approvals access,
        and allowed in the request's company. Only they get a to-do.

        Read as superuser: a requester may not read other users' groups and
        companies, and the result is only used to address activities.
        """
        self.ensure_one()
        barred = self.requester_id | self.create_uid
        company = self.company_id
        return self.category_id.sudo().approver_ids.filtered(
            lambda user: user not in barred
            and user._has_group(APPROVAL_USER_GROUP)
            and company in user.company_ids
        )

    def _write_workflow(self, vals):
        """Apply a transition the calling button has already checked. The
        user still needs write access to the records; ``sudo()`` only lifts
        the guard in ``write`` that keeps these fields from direct edits.
        Under sudo the uid is unchanged, so tracking and write_uid still
        name the user who clicked."""
        self.check_access("write")
        self.sudo().write(vals)

    # -- actions -------------------------------------------------------
    def action_submit(self):
        self._check_state(("draft",), _("submitted"))
        self._check_raised_by_or_manager(_("submit"))
        self._check_submittable()
        self._write_workflow({"state": "submitted"})
        self._schedule_approver_activities()

    def action_approve(self):
        self._check_can_decide()
        self._write_workflow(
            {
                "state": "approved",
                "approver_id": self.env.uid,
                "decision_date": fields.Datetime.now(),
                "refusal_reason": False,
            }
        )
        self._close_approver_activities()
        self._post_decision("drkds_approvals_lite.mail_template_approval_approved")

    def action_refuse(self, reason):
        """Refuse with a reason. The form goes through the wizard, which
        collects the reason; code may call this directly."""
        if not reason or not reason.strip():
            raise ValidationError(_("A refusal needs a reason."))
        self._check_can_decide()
        self._write_workflow(
            {
                "state": "refused",
                "approver_id": self.env.uid,
                "decision_date": fields.Datetime.now(),
                "refusal_reason": reason.strip(),
            }
        )
        self._close_approver_activities()
        self._post_decision("drkds_approvals_lite.mail_template_approval_refused")

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
        self._check_raised_by_or_manager(_("cancel"))
        self._write_workflow({"state": "cancelled"})
        self._close_approver_activities()

    def action_reset_to_draft(self):
        self._check_state(("refused", "cancelled"), _("reset to draft"))
        self._check_raised_by_or_manager(_("reset to draft"))
        self._write_workflow(
            {
                "state": "draft",
                "approver_id": False,
                "decision_date": False,
                "refusal_reason": False,
            }
        )

    # -- mail ----------------------------------------------------------
    def _post_decision(self, template_xmlid):
        """Post the decision mail to the requester.

        The template names its recipient (the requester), and is posted as a
        note so that only that recipient is notified. As a discussion message
        it would also go to every follower, and each approver follows the
        request through the to-do it was given; the mail is written to the
        requester, so it is theirs alone. The chatter still shows it to
        anyone who opens the request.
        """
        self.message_post_with_source(template_xmlid, subtype_xmlid="mail.mt_note")

    # -- activities ----------------------------------------------------
    def _schedule_approver_activities(self, users=None):
        """Give each decider (optionally only those among `users`) a to-do."""
        for request in self:
            deciders = request._get_deciders()
            if users is not None:
                deciders = deciders.filtered(lambda user: user.id in users.ids)
            for approver in deciders:
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

    def _close_approver_activities(self, users=None):
        """Drop the to-dos still open for the approvers (optionally only
        those of `users`).

        They are unlinked rather than marked done: a done activity would
        read as if every approver had acted, which is not what happened.
        Only automated to-dos go (the ones scheduled here); a to-do someone
        added by hand stays. Runs as superuser because mail lets a user
        delete only the activities they created or own, and the deciding
        approver is neither for the to-dos of the other approvers.
        """
        requests = self.sudo()
        if users is None:
            requests.activity_unlink(["mail.mail_activity_data_todo"])
            return
        for user in users:
            requests.activity_unlink(["mail.mail_activity_data_todo"], user_id=user.id)
