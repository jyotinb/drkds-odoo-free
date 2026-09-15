from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DrkdsBudgetLine(models.Model):
    """One budgeted figure: an account or account group, over the budget period.

    Sign convention
    ---------------
    Odoo stores every journal item as a signed ``balance``: debit positive,
    credit negative. An expense therefore accumulates a **positive** balance and
    income a **negative** one. Neither is what a finance person wants to read in
    a budget report, where both a cost budget and a revenue budget are entered
    as a plain positive number.

    So the line has a direction, taken from the accounts it covers:

    * ``expense`` - actual = ``sum(balance)``. Spending more raises the actual.
    * ``income``  - actual = ``-sum(balance)``. Collecting more raises it.

    Variance is then stated as **favourable positive** in both directions:

    * expense: ``variance = planned - actual`` (spending less is favourable)
    * income:  ``variance = actual - planned`` (collecting more is favourable)

    A line is flagged **over budget** when its variance is unfavourable, which
    means over-spend on an expense line and under-collection on an income line.
    """

    _name = "drkds.budget.line"
    _description = "Budget Line"
    _order = "budget_id, sequence, id"
    _check_company_auto = True

    budget_id = fields.Many2one(
        "drkds.budget", string="Budget", required=True,
        ondelete="cascade", index=True,
    )
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        related="budget_id.company_id", store=True, index=True, readonly=True,
    )
    currency_id = fields.Many2one(related="budget_id.currency_id", readonly=True)
    date_from = fields.Date(related="budget_id.date_from", readonly=True)
    date_to = fields.Date(related="budget_id.date_to", readonly=True)
    state = fields.Selection(related="budget_id.state", store=True, readonly=True)

    account_id = fields.Many2one(
        "account.account", string="Account",
        domain="[('company_ids', 'in', company_id)]",
        help="Budget a single general ledger account.",
    )
    account_group_id = fields.Many2one(
        "account.group", string="Account Group",
        help="Budget every account inside a group, for example all travel "
        "accounts. Use this instead of an account, not as well as one.",
    )
    analytic_account_id = fields.Many2one(
        "account.analytic.account", string="Analytic Account",
        check_company=True, ondelete="restrict",
        help="Optional. Restricts the actuals to journal items carrying this "
        "analytic account, and counts only its share of each item.",
    )

    account_ids = fields.Many2many(
        "account.account", string="Covered Accounts",
        compute="_compute_account_ids",
        help="The accounts this line actually measures: the chosen account, or "
        "every account under the chosen group.",
    )
    budget_direction = fields.Selection(
        [("expense", "Expense"), ("income", "Income")],
        string="Direction", compute="_compute_budget_direction", store=True,
        help="Expense lines go over budget by spending too much, income lines "
        "by collecting too little.",
    )

    planned_amount = fields.Monetary(
        string="Planned", required=True, default=0.0,
        currency_field="currency_id",
        help="The budgeted figure, entered as a positive amount whether the "
        "line is a cost or a revenue.",
    )
    actual_amount = fields.Monetary(
        string="Actual", compute="_compute_actual_amount",
        currency_field="currency_id",
        help="Posted journal items on the covered accounts, inside the budget "
        "period, in this company. Draft and cancelled entries are ignored.",
    )
    variance_amount = fields.Monetary(
        string="Variance", compute="_compute_variance",
        currency_field="currency_id",
        help="Favourable positive: under-spend on an expense line, "
        "over-collection on an income line.",
    )
    variance_percent = fields.Float(
        string="Variance %", compute="_compute_variance", digits=(16, 2),
        help="Variance as a percentage of the planned amount. Zero when nothing "
        "was planned, because there is no base to compare against.",
    )
    achieved_percent = fields.Float(
        string="Achieved %", compute="_compute_variance", digits=(16, 2),
        help="Actual as a percentage of planned. This is the figure to put on a "
        "progress bar.",
    )
    is_over_budget = fields.Boolean(
        string="Over Budget", compute="_compute_variance",
        help="True when the variance is unfavourable.",
    )
    name = fields.Char(string="Description")

    _planned_positive = models.Constraint(
        "check(planned_amount >= 0)",
        "A planned amount is entered as a positive figure in both directions.",
    )

    # ------------------------------------------------------------------
    # constraints
    # ------------------------------------------------------------------
    @api.constrains("account_id", "account_group_id", "budget_id")
    def _check_target(self):
        for line in self:
            if not line.account_id and not line.account_group_id:
                raise ValidationError(
                    _("A budget line needs either an account or an account group.")
                )
            if line.account_id and line.account_group_id:
                raise ValidationError(
                    _(
                        "Budget line %s targets both an account and an account "
                        "group. Pick one, or the same journal items would be "
                        "counted twice across lines.",
                        line.display_name,
                    )
                )

    # ------------------------------------------------------------------
    # compute
    # ------------------------------------------------------------------
    @api.depends("account_id", "account_group_id", "company_id")
    def _compute_account_ids(self):
        Account = self.env["account.account"]
        for line in self:
            if line.account_id:
                line.account_ids = line.account_id
            elif line.account_group_id and line.company_id:
                line.account_ids = line._accounts_in_group()
            else:
                line.account_ids = Account

    def _accounts_in_group(self):
        """Accounts whose code falls inside the group's prefix range.

        ``account.account.group_id`` is a non-stored compute with no search
        method, so it cannot be used in a domain. An account group is defined by
        a code prefix range, and that is what is matched here, the same way the
        core group assignment query does it.
        """
        self.ensure_one()
        group = self.account_group_id
        company = self.company_id
        start = group.code_prefix_start or ""
        end = group.code_prefix_end or start
        if not start:
            return self.env["account.account"]
        accounts = self.env["account.account"].sudo().search(
            [("company_ids", "in", company.ids)]
        )

        def in_range(account):
            code = account.with_company(company).code or ""
            return start <= code[: len(start)] and end >= code[: len(end)]

        return accounts.filtered(in_range).with_env(self.env)

    @api.depends("account_id", "account_group_id", "company_id")
    def _compute_budget_direction(self):
        """Income only when every covered account is an income account.

        A mixed group is treated as an expense budget, because that is the
        cautious reading: an unexpected debit should make the line look worse,
        not better.
        """
        for line in self:
            groups = set(line.account_ids.mapped("internal_group"))
            line.budget_direction = "income" if groups == {"income"} else "expense"

    @api.depends(
        "account_ids",
        "analytic_account_id",
        "budget_direction",
        "date_from",
        "date_to",
        "company_id",
    )
    def _compute_actual_amount(self):
        for line in self:
            line.actual_amount = line._get_actual_amount()

    @api.depends("planned_amount", "actual_amount", "budget_direction")
    def _compute_variance(self):
        for line in self:
            planned = line.planned_amount
            actual = line.actual_amount
            if line.budget_direction == "income":
                variance = actual - planned
            else:
                variance = planned - actual
            line.variance_amount = variance
            # Guard the division: a line planned at zero has no base to compare
            # against, and a nil budget is a legitimate thing to record.
            line.variance_percent = (variance / planned * 100.0) if planned else 0.0
            line.achieved_percent = (actual / planned * 100.0) if planned else 0.0
            line.is_over_budget = bool(
                line.currency_id.compare_amounts(variance, 0.0) < 0
                if line.currency_id
                else variance < 0
            )

    # ------------------------------------------------------------------
    # actuals
    # ------------------------------------------------------------------
    def _get_move_line_domain(self):
        """Domain selecting the journal items this line measures.

        Only ``posted`` moves count. A draft entry is a proposal, and letting it
        move a variance is the single most common way a budget report loses the
        finance team's trust.
        """
        self.ensure_one()
        if not self.account_ids or not self.date_from or not self.date_to:
            return [("id", "=", False)]
        domain = [
            ("parent_state", "=", "posted"),
            ("account_id", "in", self.account_ids.ids),
            ("date", ">=", self.date_from),
            ("date", "<=", self.date_to),
            ("company_id", "=", self.company_id.id),
        ]
        if self.analytic_account_id:
            domain.append(
                ("distribution_analytic_account_ids", "in", self.analytic_account_id.ids)
            )
        return domain

    def _get_actual_amount(self):
        """Signed actual for this line, in the company currency."""
        self.ensure_one()
        domain = self._get_move_line_domain()
        AccountMoveLine = self.env["account.move.line"].sudo()
        if self.analytic_account_id:
            # Count only the analytic share of each item, so a 40% allocation
            # does not consume 100% of the analytic budget.
            total = 0.0
            key = str(self.analytic_account_id.id)
            for move_line in AccountMoveLine.search(domain):
                distribution = move_line.analytic_distribution or {}
                percentage = 0.0
                for raw_key, raw_percentage in distribution.items():
                    if key in raw_key.split(","):
                        percentage += raw_percentage or 0.0
                total += move_line.balance * percentage / 100.0
        else:
            groups = AccountMoveLine._read_group(domain, aggregates=["balance:sum"])
            total = groups[0][0] if groups else 0.0
        total = total or 0.0
        return -total if self.budget_direction == "income" else total

    # ------------------------------------------------------------------
    # actions
    # ------------------------------------------------------------------
    def action_open_move_lines(self):
        """Drill down from a budget line to the journal items behind it."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Journal Items - %s", self.display_name),
            "res_model": "account.move.line",
            "view_mode": "list,form",
            "domain": self._get_move_line_domain(),
            "context": {"create": False, "search_default_group_by_account": 1},
        }

    @api.depends("account_id", "account_group_id", "analytic_account_id")
    def _compute_display_name(self):
        for line in self:
            target = line.account_id.display_name or line.account_group_id.display_name or _("Unset")
            if line.analytic_account_id:
                target = f"{target} / {line.analytic_account_id.display_name}"
            line.display_name = target
