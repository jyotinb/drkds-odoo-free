from odoo import api, fields, models

from .drkds_tds_register import FINANCIAL_YEAR_SQL


class DrkdsTdsYtd(models.Model):
    """Running total billed per vendor, per section, per financial year.

    The localisation already sums this figure - it is what decides whether the
    threshold alert appears on a bill - but it does so privately, inside a
    compute, one bill at a time. An accountant who wants to know before the
    quarter closes which vendors are near a limit, or which crossed one on a
    bill nobody deducted on, has nowhere to look.

    This view exposes that same aggregate as something you can open, sort and
    filter. It is built the way the localisation builds it: posted invoice
    lines whose account carries a section, summed by the vendor's PAN entity
    where there is one and by the vendor otherwise.
    """

    _name = "drkds.tds.ytd"
    _description = "TDS Year to Date by Vendor and Section"
    _auto = False
    _order = "financial_year desc, base_amount desc"
    _rec_name = "section_id"

    partner_id = fields.Many2one("res.partner", string="Vendor", readonly=True)
    pan_entity_id = fields.Many2one("l10n_in.pan.entity", string="PAN Entity", readonly=True)
    section_id = fields.Many2one("l10n_in.section.alert", string="TDS Section", readonly=True)
    financial_year = fields.Char(string="Financial Year", readonly=True)
    base_amount = fields.Monetary(
        string="Billed in Year", currency_field="currency_id", readonly=True,
        help="Sum of the posted bill lines booked to accounts carrying this section.",
    )
    bill_count = fields.Integer(string="Bills", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    currency_id = fields.Many2one(
        "res.currency", string="Currency",
        compute="_compute_currency_id",
    )
    aggregate_limit = fields.Float(
        string="Annual Threshold", related="section_id.aggregate_limit", readonly=True,
    )
    is_aggregate_limit = fields.Boolean(related="section_id.is_aggregate_limit", readonly=True)
    over_threshold = fields.Boolean(
        string="Over Threshold", compute="_compute_over_threshold", search="_search_over_threshold",
        help="The vendor has passed the section's annual threshold this year.",
    )
    deducted_amount = fields.Monetary(
        string="TDS Deducted", currency_field="currency_id",
        compute="_compute_deducted_amount",
        help="What has actually been withheld for this vendor and section in "
        "the same year, read back from the deduction register.",
    )

    def _compute_currency_id(self):
        for record in self:
            record.currency_id = record.company_id.currency_id

    @api.depends("base_amount", "section_id")
    def _compute_over_threshold(self):
        for record in self:
            section = record.section_id
            record.over_threshold = bool(
                section.is_aggregate_limit
                and section.aggregate_period == "fiscal_yearly"
                and record.base_amount > section.aggregate_limit
            )

    def _search_over_threshold(self, operator, value):
        """Resolve the filter by reading the rows, since the flag is computed.

        The ORM sends ``in`` and ``not in`` for a boolean domain as well as
        ``=`` and ``!=``, so all four have to be handled or the filter breaks.
        """
        if operator in ("in", "not in"):
            values = set(value)
            if values == {True, False}:
                return [(1, "=", 1)] if operator == "in" else [(0, "=", 1)]
            wanted = True in values
            if operator == "not in":
                wanted = not wanted
        elif operator in ("=", "!=") and isinstance(value, bool):
            wanted = value if operator == "=" else not value
        else:
            raise NotImplementedError(
                "Unsupported operator %s on over_threshold" % operator
            )
        over = self.search([]).filtered("over_threshold")
        return [("id", "in" if wanted else "not in", over.ids)]

    def _compute_deducted_amount(self):
        register = self.env["drkds.tds.register"]
        for record in self:
            rows = register.search([
                ("section_id", "=", record.section_id.id),
                ("financial_year", "=", record.financial_year),
                ("company_id", "=", record.company_id.id),
                ("partner_id", "=", record.partner_id.id),
            ])
            record.deducted_amount = sum(rows.mapped("tds_amount"))

    def action_open_bills(self):
        """Open the bills behind one row."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.display_name,
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [
                ("move_type", "in", ("in_invoice", "in_refund")),
                ("state", "=", "posted"),
                ("commercial_partner_id", "=", self.partner_id.id),
                ("company_id", "=", self.company_id.id),
                ("line_ids.account_id.l10n_in_tds_tcs_section_id", "=", self.section_id.id),
            ],
        }


    def _search(self, domain, *args, **kwargs):
        """Flush the records the view reads before querying them.

        The view is read straight from the database, so anything still sitting
        in the ORM cache - a bill posted a moment ago in the same transaction,
        for instance - would be invisible to it. Writing the pending values out
        first keeps the report honest.
        """
        self.env["account.move"].flush_model()
        self.env["account.move.line"].flush_model()
        return super()._search(domain, *args, **kwargs)

    @property
    def _table_query(self):
        date_col = "line.date"
        return f"""
            SELECT
                MIN(line.id) AS id,
                move.commercial_partner_id AS partner_id,
                partner.l10n_in_pan_entity_id AS pan_entity_id,
                account.l10n_in_tds_tcs_section_id AS section_id,
                {FINANCIAL_YEAR_SQL.format(col=date_col)} AS financial_year,
                line.company_id AS company_id,
                SUM(line.balance) AS base_amount,
                COUNT(DISTINCT move.id) AS bill_count
            FROM account_move_line line
            JOIN account_move move ON move.id = line.move_id
            JOIN account_account account ON account.id = line.account_id
            LEFT JOIN res_partner partner ON partner.id = move.commercial_partner_id
            WHERE account.l10n_in_tds_tcs_section_id IS NOT NULL
              AND move.move_type IN ('in_invoice', 'in_refund')
              AND line.parent_state = 'posted'
              AND line.display_type = 'product'
            GROUP BY
                move.commercial_partner_id,
                partner.l10n_in_pan_entity_id,
                account.l10n_in_tds_tcs_section_id,
                {FINANCIAL_YEAR_SQL.format(col=date_col)},
                line.company_id
        """
