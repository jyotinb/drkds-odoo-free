from odoo import fields, models


class DrkdsTicketStage(models.Model):
    """A column of the ticket Kanban.

    A stage is either global (no team) or restricted to one team. The two
    flags carry all the behaviour: ``folded`` collapses the column in the
    Kanban, and ``is_closed`` marks the stage as an end state, which is what
    stamps the closing date on a ticket.
    """

    _name = "drkds.ticket.stage"
    _description = "Support Ticket Stage"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    team_id = fields.Many2one(
        "drkds.ticket.team",
        string="Team",
        ondelete="cascade",
        help="Leave empty to make the stage available to every team.",
    )
    folded = fields.Boolean(
        string="Folded in Kanban",
        help="Collapse this column in the Kanban view. Typical for end states.",
    )
    is_closed = fields.Boolean(
        string="Closing Stage",
        help="A ticket entering this stage is considered closed and its closing "
        "date is stamped.",
    )
    active = fields.Boolean(default=True)
    description = fields.Text(translate=True)

    _name_team_uniq = models.Constraint(
        "unique(name, team_id)",
        "A stage with this name already exists for this team.",
    )
