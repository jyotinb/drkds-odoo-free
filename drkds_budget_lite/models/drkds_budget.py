from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class DrkdsBudget(models.Model):
    """A budget document: one period, one company, a set of budgeted lines.

    The document itself carries no accounting logic. It owns the period that
    every line measures its actual spend over, and a state that stops the
    period being moved once people have started reporting against it.
    """

    _name = "drkds.budget"
    _description = "Budget"
    _order = "date_from desc, name"
    _check_company_auto = True

    name = fields.Char(
        string="Budget", required=True, copy=False,
        help="How this budget is referred to, for example FY 2026-27 Operating Budget.",
    )
    date_from = fields.Date(
        string="From", required=True,
        default=lambda self: fields.Date.context_today(self).replace(month=4, day=1),
        help="First day included when actual spend is measured.",
    )
    date_to = fields.Date(
        string="To", required=True,
        help="Last day included when actual spend is measured.",
    )
    company_id = fields.Many2one(
        "res.company", string="Company", required=True, index=True,
        default=lambda self: self.env.company,
        help="Only journal items of this company count towards the actuals.",
    )
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", readonly=True,
        help="Budgets are held in the company currency, the same currency the "
        "journal item balances are stored in.",
    )
    user_id = fields.Many2one(
        "res.users", string="Responsible", default=lambda self: self.env.user,
        help="The person who owns this budget and answers for the variance.",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Status", default="draft", required=True, copy=False,
        help="Draft is still being written. Confirmed is in force and being "
        "reported against. Done is a closed period. Cancelled is abandoned.",
    )
    line_ids = fields.One2many(
        "drkds.budget.line", "budget_id", string="Budget Lines",
        copy=True,
    )
    note = fields.Html(string="Notes")

    planned_total = fields.Monetary(
        string="Planned", compute="_compute_totals", store=False,
        currency_field="currency_id",
    )
    actual_total = fields.Monetary(
        string="Actual", compute="_compute_totals", store=False,
        currency_field="currency_id",
    )
    variance_total = fields.Monetary(
        string="Variance", compute="_compute_totals", store=False,
        currency_field="currency_id",
        help="Sum of the line variances. Positive is favourable: under-spend on "
        "expense lines, over-collection on income lines.",
    )
    variance_percent = fields.Float(
        string="Variance %", compute="_compute_totals", store=False,
        digits=(16, 2),
    )
    line_count = fields.Integer(string="Lines", compute="_compute_totals")
    over_budget_line_count = fields.Integer(
        string="Over Budget Lines", compute="_compute_totals",
    )

    _name_company_uniq = models.Constraint(
        "unique(name, company_id)",
        "A budget with this name already exists for this company.",
    )
    _date_order = models.Constraint(
        "check(date_to >= date_from)",
        "The end of a budget period cannot be before its start.",
    )

    # ------------------------------------------------------------------
    # compute
    # ------------------------------------------------------------------
    @api.depends(
        "line_ids.planned_amount",
        "line_ids.actual_amount",
        "line_ids.variance_amount",
        "line_ids.is_over_budget",
    )
    def _compute_totals(self):
        for budget in self:
            lines = budget.line_ids
            planned = sum(lines.mapped("planned_amount"))
            budget.planned_total = planned
            budget.actual_total = sum(lines.mapped("actual_amount"))
            variance = sum(lines.mapped("variance_amount"))
            budget.variance_total = variance
            budget.variance_percent = (variance / planned * 100.0) if planned else 0.0
            budget.line_count = len(lines)
            budget.over_budget_line_count = len(lines.filtered("is_over_budget"))

    # ------------------------------------------------------------------
    # constraints
    # ------------------------------------------------------------------
    @api.constrains("company_id", "line_ids")
    def _check_line_company(self):
        for budget in self:
            wrong = budget.line_ids.filtered(
                lambda line: line.account_id and line.account_id.company_ids
                and budget.company_id not in line.account_id.company_ids
            )
            if wrong:
                raise ValidationError(
                    _(
                        "Account %(account)s does not belong to company %(company)s.",
                        account=wrong[0].account_id.display_name,
                        company=budget.company_id.display_name,
                    )
                )

    # ------------------------------------------------------------------
    # state transitions
    # ------------------------------------------------------------------
    def action_confirm(self):
        """Put the budget in force. It must have at least one line."""
        for budget in self:
            if budget.state != "draft":
                raise UserError(_("Only a draft budget can be confirmed."))
            if not budget.line_ids:
                raise UserError(
                    _("Budget %s has no lines, so there is nothing to track.", budget.name)
                )
        self.write({"state": "confirmed"})
        return True

    def action_done(self):
        """Close the budget period. Figures stay visible and keep recomputing."""
        for budget in self:
            if budget.state != "confirmed":
                raise UserError(_("Only a confirmed budget can be marked done."))
        self.write({"state": "done"})
        return True

    def action_cancel(self):
        """Abandon the budget. A done budget is history and cannot be cancelled."""
        for budget in self:
            if budget.state == "done":
                raise UserError(
                    _("Budget %s is done. Reset it to draft before cancelling.", budget.name)
                )
        self.write({"state": "cancel"})
        return True

    def action_draft(self):
        """Send the budget back to draft so its period or lines can change."""
        self.write({"state": "draft"})
        return True

    def action_open_lines(self):
        """Open this budget's lines in the budget versus actual report view."""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "drkds_budget_lite.action_drkds_budget_line_report"
        )
        action["domain"] = [("budget_id", "=", self.id)]
        action["context"] = {"search_default_group_by_account": 1}
        return action

    # ------------------------------------------------------------------
    # overrides
    # ------------------------------------------------------------------
    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for budget, vals in zip(self, vals_list):
            vals.setdefault("name", _("%s (copy)", budget.name))
            vals.setdefault("state", "draft")
        return vals_list

    def write(self, vals):
        """The period may not move once a budget is in force.

        Variance figures already circulated would silently change meaning.
        """
        if {"date_from", "date_to"} & set(vals):
            locked = self.filtered(lambda budget: budget.state in ("confirmed", "done"))
            if locked:
                raise UserError(
                    _(
                        "The period of budget %s cannot change while it is in force. "
                        "Reset it to draft first.",
                        locked[0].name,
                    )
                )
        return super().write(vals)
