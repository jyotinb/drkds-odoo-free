from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

READONLY_STATES = ("approved", "refused", "done", "cancel")


class DrkdsMaterialRequest(models.Model):
    """An internal request for material to be issued from stock.

    Odoo Community can move goods between locations, but it has no document an
    employee fills in to ask for them and no one to approve it. This model is
    that document: it carries who asked, what for, what is wanted and where it
    should go, and it walks a short, fixed state machine from draft to done.

    Fulfilment is an ordinary internal transfer created from the approved
    lines, so the stock side stays entirely standard and nothing here
    second-guesses the inventory engine.
    """

    _name = "drkds.lite.material.request"
    _description = "Material Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_request desc, id desc"

    name = fields.Char(
        string="Reference", required=True, copy=False, readonly=True,
        default=lambda self: _("New"), index=True,
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company,
        index=True,
    )
    requester_id = fields.Many2one(
        "res.users", string="Requester", required=True, index=True,
        default=lambda self: self.env.user, tracking=True,
        help="The employee asking for the material. A requester only ever sees "
        "their own requests.",
    )
    employee_id = fields.Many2one(
        "hr.employee", string="Employee", compute="_compute_employee_id",
        store=True, readonly=False,
        help="Employee record behind the requester, used to fill the department.",
    )
    department_id = fields.Many2one(
        "hr.department", string="Department", compute="_compute_department_id",
        store=True, readonly=False, index=True,
    )
    date_request = fields.Datetime(
        string="Request Date", required=True, default=fields.Datetime.now,
        tracking=True,
    )
    date_required = fields.Date(
        string="Required By", tracking=True,
        help="When the material is needed. Informative: it drives no scheduling.",
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse", string="Warehouse", required=True,
        default=lambda self: self._default_warehouse(), tracking=True,
        check_company=True,
    )
    location_id = fields.Many2one(
        "stock.location", string="Source Location", required=True,
        compute="_compute_location_id", store=True, readonly=False, precompute=True,
        domain="[('usage', 'in', ('internal', 'transit'))]",
        check_company=True,
        help="Stock the material is taken from. On-hand figures on the lines "
        "are read at this location.",
    )
    location_dest_id = fields.Many2one(
        "stock.location", string="Destination Location", required=True,
        compute="_compute_location_dest_id", store=True, readonly=False, precompute=True,
        domain="[('usage', 'in', ('internal', 'transit', 'customer', 'production'))]",
        check_company=True,
        help="Where the material should end up, for example a workshop or a "
        "site location.",
    )
    reason = fields.Text(
        string="Reason", tracking=True,
        help="Why the material is needed. The approver reads this.",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("refused", "Refused"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Status", default="draft", required=True, tracking=True,
        copy=False, index=True,
    )
    line_ids = fields.One2many(
        "drkds.lite.material.request.line", "request_id", string="Requested Material",
        copy=True,
    )
    approver_id = fields.Many2one(
        "res.users", string="Approved By", readonly=True, copy=False, tracking=True,
    )
    date_approved = fields.Datetime(string="Approval Date", readonly=True, copy=False)
    refusal_reason = fields.Text(
        string="Refusal Reason", readonly=True, copy=False, tracking=True,
        help="Recorded when a request is refused. A refusal without a reason "
        "is not accepted.",
    )
    picking_ids = fields.One2many(
        "stock.picking", string="Transfers", compute="_compute_picking_ids",
    )
    picking_count = fields.Integer(
        string="Transfer Count", compute="_compute_picking_ids"
    )
    outstanding_qty = fields.Float(
        string="Outstanding", compute="_compute_outstanding_qty", store=True,
        digits="Product Unit",
        help="Total quantity still to be delivered across all lines.",
    )
    is_fully_fulfilled = fields.Boolean(
        string="Fully Fulfilled", compute="_compute_outstanding_qty", store=True,
    )

    _name_uniq = models.Constraint(
        "unique(name, company_id)",
        "A material request reference must be unique per company.",
    )

    # ------------------------------------------------------------------
    # defaults and computes
    # ------------------------------------------------------------------
    @api.model
    def _default_warehouse(self):
        return self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )

    @api.depends("requester_id")
    def _compute_employee_id(self):
        for request in self:
            employee = self.env["hr.employee"].sudo().search(
                [
                    ("user_id", "=", request.requester_id.id),
                    ("company_id", "=", request.company_id.id),
                ],
                limit=1,
            )
            request.employee_id = employee

    @api.depends("employee_id")
    def _compute_department_id(self):
        for request in self:
            request.department_id = request.employee_id.sudo().department_id

    @api.depends("warehouse_id")
    def _compute_location_id(self):
        for request in self:
            request.location_id = request.warehouse_id.lot_stock_id

    @api.depends("warehouse_id")
    def _compute_location_dest_id(self):
        for request in self:
            picking_type = request.warehouse_id.int_type_id
            request.location_dest_id = (
                picking_type.default_location_dest_id
                or request.warehouse_id.lot_stock_id
            )

    @api.depends("line_ids.move_ids.picking_id")
    def _compute_picking_ids(self):
        for request in self:
            pickings = request.line_ids.move_ids.picking_id
            request.picking_ids = pickings
            request.picking_count = len(pickings)

    @api.depends("line_ids.qty_outstanding", "line_ids.product_qty", "state")
    def _compute_outstanding_qty(self):
        for request in self:
            outstanding = sum(request.line_ids.mapped("qty_outstanding"))
            request.outstanding_qty = outstanding
            request.is_fully_fulfilled = bool(request.line_ids) and not outstanding

    # ------------------------------------------------------------------
    # constraints
    # ------------------------------------------------------------------
    @api.constrains("location_id", "location_dest_id")
    def _check_locations(self):
        for request in self:
            if request.location_id and request.location_id == request.location_dest_id:
                raise ValidationError(
                    _("The source and destination locations of %s must differ.",
                      request.display_name)
                )

    # ------------------------------------------------------------------
    # orm
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                company_id = vals.get("company_id") or self.env.company.id
                vals["name"] = self.env["ir.sequence"].with_company(
                    company_id
                ).next_by_code("drkds.lite.material.request") or _("New")
        return super().create(vals_list)

    def write(self, vals):
        protected = {"line_ids", "warehouse_id", "location_id", "location_dest_id"}
        if protected & set(vals):
            locked = self.filtered(lambda r: r.state in READONLY_STATES)
            if locked:
                raise UserError(
                    _("The content of %s can no longer be changed in state %s.",
                      ", ".join(locked.mapped("display_name")),
                      locked[0].state)
                )
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_only_draft_or_cancel(self):
        for request in self:
            if request.state not in ("draft", "cancel"):
                raise UserError(
                    _("%s can only be deleted while it is draft or cancelled.",
                      request.display_name)
                )

    # ------------------------------------------------------------------
    # state machine
    # ------------------------------------------------------------------
    def _check_transition(self, allowed, target):
        """Refuse any transition the workflow does not define."""
        wrong = self.filtered(lambda r: r.state not in allowed)
        if wrong:
            raise UserError(
                _("%(name)s is %(state)s and cannot be moved to %(target)s.",
                  name=wrong[0].display_name,
                  state=dict(self._fields["state"].selection)[wrong[0].state],
                  target=dict(self._fields["state"].selection)[target])
            )

    def action_submit(self):
        self._check_transition({"draft", "refused"}, "submitted")
        for request in self:
            if not request.line_ids:
                raise UserError(
                    _("%s has no lines, there is nothing to request.",
                      request.display_name)
                )
        self.write({"state": "submitted", "refusal_reason": False})
        return True

    def action_reset_to_draft(self):
        self._check_transition({"submitted", "refused", "cancel"}, "draft")
        self.write({
            "state": "draft",
            "approver_id": False,
            "date_approved": False,
            "refusal_reason": False,
        })
        return True

    def action_approve(self):
        """Approve and immediately raise the internal transfer for the lines."""
        self._check_transition({"submitted"}, "approved")
        for request in self:
            if request.requester_id == self.env.user:
                raise UserError(
                    _("%s was raised by you. Someone else has to approve it.",
                      request.display_name)
                )
            request.write({
                "state": "approved",
                "approver_id": self.env.user.id,
                "date_approved": fields.Datetime.now(),
                "refusal_reason": False,
            })
            request._create_transfer()
        return True

    def action_refuse(self):
        """Open the wizard that captures the mandatory refusal reason."""
        self._check_transition({"submitted"}, "refused")
        return {
            "type": "ir.actions.act_window",
            "name": _("Refuse Material Request"),
            "res_model": "drkds.lite.material.request.refuse",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    def action_refuse_with_reason(self, reason):
        """Refuse the request, recording why. An empty reason is rejected."""
        self._check_transition({"submitted"}, "refused")
        reason = (reason or "").strip()
        if not reason:
            raise UserError(_("A refusal must say why the request is turned down."))
        self.write({
            "state": "refused",
            "refusal_reason": reason,
            "approver_id": self.env.user.id,
            "date_approved": fields.Datetime.now(),
        })
        return True

    def action_cancel(self):
        self._check_transition({"draft", "submitted", "approved", "refused"}, "cancel")
        for request in self:
            request.line_ids.move_ids.picking_id.filtered(
                lambda p: p.state not in ("done", "cancel")
            ).action_cancel()
        self.write({"state": "cancel"})
        return True

    # ------------------------------------------------------------------
    # fulfilment
    # ------------------------------------------------------------------
    def _create_transfer(self):
        """Create one internal transfer holding every outstanding line."""
        self.ensure_one()
        picking_type = self.warehouse_id.int_type_id
        if not picking_type:
            raise UserError(
                _("Warehouse %s has no internal transfer operation type.",
                  self.warehouse_id.display_name)
            )
        move_vals = [
            line._prepare_stock_move_vals()
            for line in self.line_ids
            if line.qty_outstanding > 0
        ]
        if not move_vals:
            return self.env["stock.picking"]
        picking = self.env["stock.picking"].create({
            "picking_type_id": picking_type.id,
            "location_id": self.location_id.id,
            "location_dest_id": self.location_dest_id.id,
            "origin": self.name,
            "company_id": self.company_id.id,
            "move_ids": [fields.Command.create(vals) for vals in move_vals],
        })
        picking.action_confirm()
        return picking

    def action_create_transfer(self):
        """Raise a further transfer for whatever is still outstanding."""
        self._check_transition({"approved"}, "approved")
        for request in self:
            if not request._create_transfer():
                raise UserError(
                    _("Nothing is outstanding on %s.", request.display_name)
                )
        return True

    def _check_fulfilment(self):
        """Close a request once every line has been delivered in full."""
        for request in self:
            if request.state == "approved" and request.is_fully_fulfilled:
                request.state = "done"

    def action_view_pickings(self):
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "name": _("Transfers"),
            "res_model": "stock.picking",
            "domain": [("id", "in", self.picking_ids.ids)],
            "view_mode": "list,form",
            "context": {"create": False},
        }
        if len(self.picking_ids) == 1:
            action.update(view_mode="form", res_id=self.picking_ids.id)
        return action
