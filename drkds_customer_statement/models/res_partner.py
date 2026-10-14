from datetime import timedelta

from odoo import _, api, fields, models

#: Ageing buckets, in days past due as at the statement date. The first
#: bucket also holds amounts not yet due, so the four buckets always add up
#: to the total outstanding.
BUCKETS = (
    ("b0_30", 0, 30),
    ("b31_60", 31, 60),
    ("b61_90", 61, 90),
    ("b90_plus", 91, None),
)

RECEIVABLE = ("asset_receivable",)
PAYABLE = ("liability_payable",)

#: Who may read the ageing fields: the same groups core uses for the
#: partner's ``credit`` and ``total_invoiced``. Anyone else either cannot
#: read journal items or reads only part of them through record rules.
ACCOUNTING_GROUPS = "account.group_account_invoice,account.group_account_readonly"


def _empty_ageing():
    """Every ageing bucket and the total at zero."""
    result = {key: 0.0 for key, _lo, _hi in BUCKETS}
    result["total"] = 0.0
    return result


class ResPartner(models.Model):
    """Statement of account engine, plus ageing figures on the partner form.

    Every figure is in the company currency and is read from posted
    receivable (and optionally payable) journal items of the partner and its
    contacts, in the company and its branches. Nothing here is stored: the
    ageing fields are recomputed on every read, for the current company, as
    at today.
    """

    _inherit = "res.partner"

    drkds_stmt_currency_id = fields.Many2one(
        "res.currency", compute="_compute_drkds_statement_ageing",
        string="Statement Currency", groups=ACCOUNTING_GROUPS,
    )
    drkds_stmt_0_30 = fields.Monetary(
        string="0-30 Days", compute="_compute_drkds_statement_ageing",
        currency_field="drkds_stmt_currency_id", groups=ACCOUNTING_GROUPS,
    )
    drkds_stmt_31_60 = fields.Monetary(
        string="31-60 Days", compute="_compute_drkds_statement_ageing",
        currency_field="drkds_stmt_currency_id", groups=ACCOUNTING_GROUPS,
    )
    drkds_stmt_61_90 = fields.Monetary(
        string="61-90 Days", compute="_compute_drkds_statement_ageing",
        currency_field="drkds_stmt_currency_id", groups=ACCOUNTING_GROUPS,
    )
    drkds_stmt_90_plus = fields.Monetary(
        string="Over 90 Days", compute="_compute_drkds_statement_ageing",
        currency_field="drkds_stmt_currency_id", groups=ACCOUNTING_GROUPS,
    )
    drkds_stmt_total_due = fields.Monetary(
        string="Total Due", compute="_compute_drkds_statement_ageing",
        currency_field="drkds_stmt_currency_id", groups=ACCOUNTING_GROUPS,
    )

    @api.depends_context("company")
    def _compute_drkds_statement_ageing(self):
        today = fields.Date.context_today(self)
        company = self.env.company
        for partner in self:
            # The contact form computes these on an unsaved copy of the
            # partner, whose id is a NewId that no journal item can point to.
            # Its figures are those of the saved partner it copies; a new
            # contact has none yet.
            saved = partner._origin
            buckets = (saved._drkds_statement_ageing(today, company=company)
                       if saved else _empty_ageing())
            partner.drkds_stmt_currency_id = company.currency_id
            partner.drkds_stmt_0_30 = buckets["b0_30"]
            partner.drkds_stmt_31_60 = buckets["b31_60"]
            partner.drkds_stmt_61_90 = buckets["b61_90"]
            partner.drkds_stmt_90_plus = buckets["b90_plus"]
            partner.drkds_stmt_total_due = buckets["total"]

    # -- engine ----------------------------------------------------------
    def _drkds_statement_account_types(self, include_vendor=False):
        return RECEIVABLE + (PAYABLE if include_vendor else ())

    def _drkds_statement_domain(self, company, include_vendor=False):
        """Posted receivable (and payable) items of this partner and its contacts.

        A branch is part of the same legal entity and posts to the same
        receivable account, so the company's statement includes its branches
        (core's partner ``credit`` counts them too). A branch's own statement
        shows only what that branch posted.
        """
        self.ensure_one()
        return [
            ("company_id", "child_of", company.id),
            ("parent_state", "=", "posted"),
            ("partner_id", "child_of", self.commercial_partner_id.id),
            ("account_id.account_type", "in",
             self._drkds_statement_account_types(include_vendor)),
            ("display_type", "not in", ("line_section", "line_note")),
        ]

    @api.model
    def _drkds_residual_at(self, lines, date_to):
        """Residual of each line as it stood on ``date_to``.

        A partial reconciliation only counts once both sides exist, which is
        its ``max_date``. Replaying the partials dated on or before the
        statement date gives the amount that was open then, so a statement
        reprinted for a past month shows what the customer owed at the time,
        not what they owe today.

        :return: ``{line id: (company-currency residual, residual in the
            line's own currency)}``. The second figure is what a customer
            invoiced in a foreign currency still has to pay in it.
        """
        residual = {line.id: [line.balance, line.amount_currency] for line in lines}
        if not lines:
            return {}
        partials = self.env["account.partial.reconcile"].search([
            "|",
            ("debit_move_id", "in", lines.ids),
            ("credit_move_id", "in", lines.ids),
            ("max_date", "<=", date_to),
        ])
        for partial in partials:
            if partial.debit_move_id.id in residual:
                residual[partial.debit_move_id.id][0] -= partial.amount
                residual[partial.debit_move_id.id][1] -= partial.debit_amount_currency
            if partial.credit_move_id.id in residual:
                residual[partial.credit_move_id.id][0] += partial.amount
                residual[partial.credit_move_id.id][1] += partial.credit_amount_currency
        return {line_id: tuple(amounts) for line_id, amounts in residual.items()}

    def _drkds_statement_ageing(self, date_to, company=None, include_vendor=False):
        """Outstanding amounts as at ``date_to`` split into ageing buckets."""
        self.ensure_one()
        company = company or self.env.company
        currency = company.currency_id
        lines = self.env["account.move.line"].search(
            self._drkds_statement_domain(company, include_vendor)
            + [("date", "<=", date_to)]
        )
        residual = self._drkds_residual_at(lines, date_to)
        result = _empty_ageing()
        for line in lines:
            amount = residual[line.id][0]
            if currency.is_zero(amount):
                continue
            days = (date_to - (line.date_maturity or line.date)).days
            result[self._drkds_bucket_for(days)] += amount
            result["total"] += amount
        return {key: currency.round(value) for key, value in result.items()}

    @api.model
    def _drkds_bucket_for(self, days):
        for key, low, high in BUCKETS:
            if high is None or days <= high:
                return key
        return BUCKETS[-1][0]

    def _drkds_statement_data(self, date_from, date_to, statement_type="activity",
                              include_vendor=False, company=None):
        """Everything the statement PDF needs for one partner, as plain values.

        ``activity`` lists every posted movement between the two dates with
        the balance brought forward as the opening line. ``outstanding``
        lists only the items still open at ``date_to``, each at the amount
        that was open then, with no opening balance.

        A line in a foreign currency carries its amount in that currency
        (the open amount for ``outstanding``). Lines with no foreign amount,
        such as exchange differences, carry none.
        """
        self.ensure_one()
        company = company or self.env.company
        currency = company.currency_id
        Line = self.env["account.move.line"]
        domain = self._drkds_statement_domain(company, include_vendor)

        if statement_type == "outstanding":
            candidates = Line.search(domain + [("date", "<=", date_to)],
                                     order="date, id")
            residual = self._drkds_residual_at(candidates, date_to)
            opening = 0.0
            lines = [(line, *residual[line.id]) for line in candidates
                     if not currency.is_zero(residual[line.id][0])]
        else:
            opening = sum(Line.search(domain + [("date", "<", date_from)])
                          .mapped("balance"))
            lines = [
                (line, line.balance, line.amount_currency) for line in Line.search(
                    domain + [("date", ">=", date_from), ("date", "<=", date_to)],
                    order="date, id",
                )
            ]

        running = currency.round(opening)
        rows = []
        for line, amount, amount_currency in lines:
            running = currency.round(running + amount)
            foreign = (line.currency_id != currency
                       and not line.currency_id.is_zero(amount_currency))
            rows.append({
                "date": line.date,
                "document": line.move_id.name,
                "reference": line.move_id.ref or line.name or "",
                "due_date": line.date_maturity,
                "debit": amount if amount > 0 else 0.0,
                "credit": -amount if amount < 0 else 0.0,
                "balance": running,
                "currency": line.currency_id if foreign else False,
                "amount_currency": amount_currency if foreign else 0.0,
                "line": line,
            })

        return {
            "partner": self,
            "company": company,
            "currency": currency,
            "date_from": date_from,
            "date_to": date_to,
            "statement_type": statement_type,
            "include_vendor": include_vendor,
            "opening_balance": currency.round(opening),
            "lines": rows,
            "closing_balance": running,
            "total_debit": currency.round(sum(r["debit"] for r in rows)),
            "total_credit": currency.round(sum(r["credit"] for r in rows)),
            "ageing": self._drkds_statement_ageing(
                date_to, company=company, include_vendor=include_vendor),
            # Deleting a bank account only archives it in Odoo 19, so the
            # setting can still point at an account the company closed.
            "bank": company.drkds_statement_bank_id.filtered("active"),
            "note": company.drkds_statement_note,
        }

    # -- UI --------------------------------------------------------------
    def action_drkds_open_statement(self):
        """Smart button: open the statement wizard for this partner."""
        self.ensure_one()
        today = fields.Date.context_today(self)
        return {
            "type": "ir.actions.act_window",
            "name": _("Statement of Account"),
            "res_model": "drkds.statement.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_partner_ids": [(6, 0, self.ids)],
                "default_date_from": today - timedelta(days=90),
                "default_date_to": today,
            },
        }
