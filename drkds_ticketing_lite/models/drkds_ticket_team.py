from odoo import api, fields, models


class DrkdsTicketTeam(models.Model):
    """A group of people who answer tickets together.

    The team is the unit of visibility: a support user sees the tickets of the
    teams they are a member of. It also carries the default assignee, applied
    when a ticket is created without one.
    """

    _name = "drkds.ticket.team"
    _description = "Support Ticket Team"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )
    member_ids = fields.Many2many(
        "res.users",
        "drkds_ticket_team_users_rel",
        "team_id",
        "user_id",
        string="Members",
        domain=lambda self: [("all_group_ids", "in", self.env.ref("base.group_user").id)],
        help="Users who work on this team's tickets and may read them.",
    )
    default_user_id = fields.Many2one(
        "res.users",
        string="Default Assignee",
        help="Assigned to new tickets of this team when no assignee is given.",
    )
    ticket_count = fields.Integer(compute="_compute_ticket_count")
    open_ticket_count = fields.Integer(compute="_compute_ticket_count")

    _name_uniq = models.Constraint(
        "unique(name)",
        "A support team with this name already exists.",
    )

    def _compute_ticket_count(self):
        Ticket = self.env["drkds.ticket"]
        total = dict(
            Ticket._read_group(
                [("team_id", "in", self.ids)], ["team_id"], ["__count"]
            )
        )
        opened = dict(
            Ticket._read_group(
                [("team_id", "in", self.ids), ("stage_id.is_closed", "=", False)],
                ["team_id"],
                ["__count"],
            )
        )
        for team in self:
            team.ticket_count = total.get(team, 0)
            team.open_ticket_count = opened.get(team, 0)

    @api.onchange("default_user_id")
    def _onchange_default_user_id(self):
        """Keep the default assignee inside the team."""
        for team in self:
            if team.default_user_id and team.default_user_id not in team.member_ids:
                team.member_ids = [fields.Command.link(team.default_user_id.id)]

    def action_view_tickets(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "drkds_ticketing_lite.action_drkds_ticket"
        )
        action["domain"] = [("team_id", "=", self.id)]
        action["context"] = {"default_team_id": self.id}
        return action
