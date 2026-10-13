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


class ResPartner(models.Model):
    """Statement of account engine, plus ageing figures on the partner form.

    Every figure is in the company currency and is read from posted
    receivable (and optionally payable) journal items of the partner and its
    contacts. Nothing here is stored: the ageing fields are recomputed on
    every read, for the current company, as at today.
    """

    _inherit = "res.partner"

    drkds_stmt_currency_id = fields.Many2one(
        "res.currency", compute="_compute_drkds_statement_ageing",
        string="Statement Currency",
    )
    drkds_stmt_0_30 = fields.Monetary(
        string="0-30 Days", compute="_compute_drkds_statement_ageing",
        currency_field="drkds_stmt_currency_id",
    )
    drkds_stmt_31_60 = fields.Monetary(
        string="31-60 Days", compute="_compute_drkds_statement_ageing",
        currency_field="drkds_stmt_currency_id",
    )
    drkds_stmt_61_90 = fields.Monetary(
        string="61-90 Days", compute="_compute_drkds_statement_ageing",
        currency_field="drkds_stmt_currency_id",
    )
    drkds_stmt_90_plus = fields.Monetary(
        string="Over 90 Days", compute="_compute_drkds_statement_ageing",
        currency_field="drkds_stmt_currency_id",
    )
    drkds_stmt_total_due = fields.Monetary(
        string="Total Due", compute="_compute_drkds_statement_ageing",
        currency_field="drkds_stmt_currency_id",
    )

    @api.depends_context("company")
    def _compute_drkds_statement_ageing(self):
        today = fields.Date.context_today(self)
        company = self.env.company
        for partner in self:
            buckets = partner._drkds_statement_ageing(today, company=company)
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
        """Posted receivable (and payable) items of this partner and its contacts."""
        self.ensure_one()
        return [
            ("company_id", "=", company.id),
            ("parent_state", "=", "posted"),
            ("partner_id", "child_of", self.commercial_partner_id.id),
            ("account_id.account_type", "in",
             self._drkds_statement_account_types(include_vendor)),
            ("display_type", "not in", ("line_section", "line_note")),
        ]

    @api.model
    def _drkds_residual_at(self, lines, date_to):
        """Company-currency residual of each line as it stood on ``date_to``.

        A partial reconciliation only counts once both sides exist, which is
        its ``max_date``. Replaying the partials dated on or before the
        statement date gives the amount that was open then, so a statement
        reprinted for a past month shows what the customer owed at the time,
        not what they owe today.
        """
        residual = {line.id: line.balance for line in lines}
        if not lines:
            return residual
        partials = self.env["account.partial.reconcile"].search([
            "|",
            ("debit_move_id", "in", lines.ids),
            ("credit_move_id", "in", lines.ids),
            ("max_date", "<=", date_to),
        ])
        for partial in partials:
            if partial.debit_move_id.id in residual:
                residual[partial.debit_move_id.id] -= partial.amount
            if partial.credit_move_id.id in residual:
                residual[partial.credit_move_id.id] += partial.amount
        return residual

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
        result = {key: 0.0 for key, _lo, _hi in BUCKETS}
        result["total"] = 0.0
        for line in lines:
            amount = residual[line.id]
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
            lines = [(line, residual[line.id]) for line in candidates
                     if not currency.is_zero(residual[line.id])]
        else:
            opening = sum(Line.search(domain + [("date", "<", date_from)])
                          .mapped("balance"))
            lines = [
                (line, line.balance) for line in Line.search(
                    domain + [("date", ">=", date_from), ("date", "<=", date_to)],
                    order="date, id",
                )
            ]

        running = currency.round(opening)
        rows = []
        for line, amount in lines:
            running = currency.round(running + amount)
            rows.append({
                "date": line.date,
                "document": line.move_id.name,
                "reference": line.move_id.ref or line.name or "",
                "due_date": line.date_maturity,
                "debit": amount if amount > 0 else 0.0,
                "credit": -amount if amount < 0 else 0.0,
                "balance": running,
                "currency": line.currency_id if line.currency_id != currency else False,
                "amount_currency": line.amount_currency,
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
            "bank": company.drkds_statement_bank_id,
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
