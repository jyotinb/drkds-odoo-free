from odoo import fields, models

#: April to March, the statutory year for TDS, regardless of the company's
#: own fiscal year setting. Returns the label and the quarter of ``column``.
FINANCIAL_YEAR_SQL = """
    CASE
        WHEN EXTRACT(MONTH FROM {col}) >= 4
        THEN EXTRACT(YEAR FROM {col})::int
        ELSE EXTRACT(YEAR FROM {col})::int - 1
    END::text || '-' || RIGHT((
        CASE
            WHEN EXTRACT(MONTH FROM {col}) >= 4
            THEN EXTRACT(YEAR FROM {col})::int + 1
            ELSE EXTRACT(YEAR FROM {col})::int
        END)::text, 2)
"""

QUARTER_SQL = """
    CASE
        WHEN EXTRACT(MONTH FROM {col}) BETWEEN 4 AND 6 THEN 'Q1'
        WHEN EXTRACT(MONTH FROM {col}) BETWEEN 7 AND 9 THEN 'Q2'
        WHEN EXTRACT(MONTH FROM {col}) BETWEEN 10 AND 12 THEN 'Q3'
        ELSE 'Q4'
    END
"""


class DrkdsTdsRegister(models.Model):
    """Line level register of the deductions the localisation has posted.

    Odoo's Indian localisation posts every deduction as its own withholding
    journal entry and reports the totals through the TDS tax report. What it
    does not offer is the flat list a Form 26Q working paper is built from:
    one row per deduction, carrying the vendor, the PAN, the section, the
    base, the rate, the amount and the bill it came off.

    This is a database view over those withholding entries, so it cannot drift
    away from them. Correct a withhold and the register follows; there is
    nothing here to reconcile.
    """

    _name = "drkds.tds.register"
    _description = "TDS Deduction Register"
    _auto = False
    _order = "date desc, id desc"
    _rec_name = "withhold_move_id"

    withhold_move_id = fields.Many2one("account.move", string="TDS Entry", readonly=True)
    move_id = fields.Many2one("account.move", string="Bill", readonly=True)
    payment_id = fields.Many2one("account.payment", string="Payment", readonly=True)
    date = fields.Date(string="Deduction Date", readonly=True)
    financial_year = fields.Char(string="Financial Year", readonly=True)
    quarter = fields.Char(
        string="Quarter", readonly=True,
        help="Return quarter of the April to March year: Q1 is April to June.",
    )
    partner_id = fields.Many2one("res.partner", string="Vendor", readonly=True)
    pan = fields.Char(string="PAN", readonly=True)
    section_id = fields.Many2one("l10n_in.section.alert", string="TDS Section", readonly=True)
    tax_id = fields.Many2one("account.tax", string="TDS Rate", readonly=True)
    base_amount = fields.Monetary(string="Base", currency_field="currency_id", readonly=True)
    rate = fields.Float(string="Rate (%)", digits=(5, 3), readonly=True)
    tds_amount = fields.Monetary(string="TDS", currency_field="currency_id", readonly=True)
    no_pan = fields.Boolean(
        string="No PAN", readonly=True,
        help="The vendor had no PAN entity when the deduction was posted.",
    )
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    state = fields.Selection(
        [("draft", "Draft"), ("posted", "Posted")], string="Status", readonly=True,
    )


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
        date_col = "withhold.date"
        return f"""
            SELECT
                line.id AS id,
                withhold.id AS withhold_move_id,
                withhold.l10n_in_withholding_ref_move_id AS move_id,
                withhold.l10n_in_withholding_ref_payment_id AS payment_id,
                withhold.date AS date,
                {FINANCIAL_YEAR_SQL.format(col=date_col)} AS financial_year,
                {QUARTER_SQL.format(col=date_col)} AS quarter,
                withhold.commercial_partner_id AS partner_id,
                pan.name AS pan,
                tax.l10n_in_section_id AS section_id,
                tax.id AS tax_id,
                ABS(line.price_subtotal) AS base_amount,
                ABS(tax.amount) AS rate,
                ABS(line.price_total - line.price_subtotal) AS tds_amount,
                partner.l10n_in_pan_entity_id IS NULL AS no_pan,
                withhold.currency_id AS currency_id,
                withhold.company_id AS company_id,
                withhold.state AS state
            FROM account_move_line line
            JOIN account_move withhold ON withhold.id = line.move_id
            JOIN account_move_line_account_tax_rel rel ON rel.account_move_line_id = line.id
            JOIN account_tax tax ON tax.id = rel.account_tax_id
            LEFT JOIN res_partner partner ON partner.id = withhold.commercial_partner_id
            LEFT JOIN l10n_in_pan_entity pan ON pan.id = partner.l10n_in_pan_entity_id
            WHERE withhold.l10n_in_is_withholding = TRUE
              AND withhold.state != 'cancel'
              AND tax.l10n_in_tax_type = 'tds_purchase'
              AND tax.l10n_in_section_id IS NOT NULL
        """
