from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

PRIORITIES = [
    ("0", "Low"),
    ("1", "Normal"),
    ("2", "High"),
    ("3", "Urgent"),
]


class DrkdsTicketTag(models.Model):
    """A free label on a ticket, for slicing a backlog any way a team likes."""

    _name = "drkds.ticket.tag"
    _description = "Support Ticket Tag"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    color = fields.Integer(string="Colour")

    _name_uniq = models.Constraint("unique(name)", "A tag with this name already exists.")


class DrkdsTicket(models.Model):
    """A customer request being worked on by a support team.

    The number comes from a sequence and never changes. The stage drives the
    lifecycle: entering a stage flagged as closing stamps ``date_closed``,
    leaving it clears the stamp again, so a reopened ticket does not keep a
    stale closing date.
    """

    _name = "drkds.ticket"
    _description = "Support Ticket"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "priority desc, id desc"
    _rec_names_search = ["name", "number"]

    number = fields.Char(
        string="Reference", required=True, copy=False, readonly=True, default="/", index=True
    )
    name = fields.Char(string="Subject", required=True, tracking=True)
    description = fields.Html(string="Description", sanitize_style=True)
    active = fields.Boolean(default=True)

    partner_id = fields.Many2one("res.partner", string="Customer", tracking=True, index=True)
    partner_email = fields.Char(string="Email", tracking=True)

    team_id = fields.Many2one(
        "drkds.ticket.team",
        string="Team",
        tracking=True,
        index=True,
        default=lambda self: self._default_team_id(),
    )
    user_id = fields.Many2one(
        "res.users",
        string="Assigned To",
        tracking=True,
        index=True,
        domain="[('share', '=', False)]",
    )
    stage_id = fields.Many2one(
        "drkds.ticket.stage",
        string="Stage",
        group_expand="_read_group_stage_ids",
        domain="['|', ('team_id', '=', False), ('team_id', '=', team_id)]",
        default=lambda self: self._default_stage_id(),
        tracking=True,
        index=True,
        ondelete="restrict",
    )
    priority = fields.Selection(PRIORITIES, default="1", tracking=True, index=True)
    tag_ids = fields.Many2many("drkds.ticket.tag", string="Tags")
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company, index=True
    )

    date_closed = fields.Datetime(string="Closing Date", readonly=True, copy=False)
    is_closed = fields.Boolean(
        string="Closed", related="stage_id.is_closed", store=True, readonly=True
    )
    kanban_state = fields.Selection(
        [("normal", "In Progress"), ("blocked", "Blocked"), ("done", "Ready")],
        default="normal",
        string="Kanban State",
    )
    color = fields.Integer(string="Colour")

    _number_uniq = models.Constraint(
        "unique(number)",
        "A ticket with this reference already exists.",
    )

    # -- defaults ------------------------------------------------------
    @api.model
    def _default_team_id(self):
        """First team the current user belongs to, if any."""
        return self.env["drkds.ticket.team"].search(
            [("member_ids", "in", self.env.uid)], limit=1
        )

    @api.model
    def _default_stage_id(self):
        team = self.env.context.get("default_team_id") or self._default_team_id()
        team_id = team.id if hasattr(team, "id") else team
        return self._first_stage(team_id)

    @api.model
    def _first_stage(self, team_id=False):
        domain = [("team_id", "in", [team_id, False] if team_id else [False])]
        return self.env["drkds.ticket.stage"].search(domain, order="sequence, id", limit=1)

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        """Show every reachable stage as a Kanban column, even the empty ones."""
        team_id = self.env.context.get("default_team_id")
        stage_domain = [("team_id", "in", [team_id, False])] if team_id else []
        return stages.search(stage_domain, order="sequence, id")

    # -- constraints ---------------------------------------------------
    @api.constrains("stage_id", "team_id")
    def _check_stage_team(self):
        for ticket in self:
            stage_team = ticket.stage_id.team_id
            if stage_team and ticket.team_id != stage_team:
                raise ValidationError(
                    _(
                        "Stage %(stage)s belongs to team %(team)s and cannot be used here.",
                        stage=ticket.stage_id.name,
                        team=stage_team.name,
                    )
                )

    # -- onchange ------------------------------------------------------
    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id and not self.partner_email:
            self.partner_email = self.partner_id.email

    @api.onchange("team_id")
    def _onchange_team_id(self):
        if self.team_id:
            if not self.user_id:
                self.user_id = self.team_id.default_user_id
            if not self.stage_id or self.stage_id.team_id != self.team_id:
                self.stage_id = self._first_stage(self.team_id.id)

    # -- CRUD ----------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("number") or vals["number"] == "/":
                vals["number"] = self.env["ir.sequence"].next_by_code("drkds.ticket") or "/"
            team = self.env["drkds.ticket.team"].browse(vals.get("team_id")).exists()
            if team and not vals.get("user_id"):
                vals["user_id"] = team.default_user_id.id or False
            if not vals.get("stage_id"):
                vals["stage_id"] = self._first_stage(vals.get("team_id")).id
            if not vals.get("partner_email") and vals.get("partner_id"):
                vals["partner_email"] = (
                    self.env["res.partner"].browse(vals["partner_id"]).email
                )
        tickets = super().create(vals_list)
        tickets._sync_date_closed()
        return tickets

    def write(self, vals):
        result = super().write(vals)
        if "stage_id" in vals:
            self._sync_date_closed()
        return result

    def _sync_date_closed(self):
        """Stamp or clear the closing date to match the current stage."""
        for ticket in self:
            if ticket.stage_id.is_closed and not ticket.date_closed:
                ticket.date_closed = fields.Datetime.now()
            elif not ticket.stage_id.is_closed and ticket.date_closed:
                ticket.date_closed = False

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for vals in vals_list:
            vals["number"] = "/"
        return vals_list

    @api.depends("number", "name")
    def _compute_display_name(self):
        for ticket in self:
            ticket.display_name = (
                f"{ticket.number} {ticket.name}" if ticket.number != "/" else ticket.name
            )

    # -- actions -------------------------------------------------------
    def action_assign_to_me(self):
        self.write({"user_id": self.env.uid})

    def action_close(self):
        """Move to the first closing stage reachable from the ticket's team."""
        for ticket in self:
            stage = self.env["drkds.ticket.stage"].search(
                [
                    ("is_closed", "=", True),
                    ("team_id", "in", [ticket.team_id.id, False]),
                ],
                order="sequence, id",
                limit=1,
            )
            if not stage:
                raise ValidationError(
                    _("No closing stage is defined for team %s.", ticket.team_id.display_name)
                )
            ticket.stage_id = stage
