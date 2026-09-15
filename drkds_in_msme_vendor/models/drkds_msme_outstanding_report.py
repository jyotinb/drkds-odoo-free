from odoo import fields, models
from odoo.tools import SQL


class DrkdsMsmeOutstandingReport(models.Model):
    """Read-only view of unpaid bills owed to registered micro and small vendors.

    Everything that moves with the calendar - days outstanding, the ageing
    bucket, whether the bill falls in the current Indian financial year - is
    computed in SQL against ``CURRENT_DATE``. That keeps the figures correct
    every morning without a nightly job, and lets the auditor group and filter
    on them natively.

    Medium enterprises never appear here. Section 15 of the MSMED Act, the
    limitation period referred to by section 43B(h) of the Income Tax Act,
    covers micro and small suppliers only.
    """

    _name = "drkds.msme.outstanding.report"
    _description = "MSME Outstanding Payments"
    _auto = False
    _rec_name = "move_id"
    _order = "days_overdue desc, msme_due_date"

    move_id = fields.Many2one("account.move", string="Bill", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Vendor", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True)
    invoice_date = fields.Date(string="Bill Date", readonly=True)
    acceptance_date = fields.Date(string="Acceptance Date", readonly=True)
    msme_due_date = fields.Date(string="MSME Due Date", readonly=True)
    limit_days = fields.Integer(string="Limit (Days)", readonly=True)
    msme_category = fields.Selection(
        selection=[("micro", "Micro"), ("small", "Small")],
        string="Enterprise Category", readonly=True,
    )
    udyam_number = fields.Char(string="Udyam Number", readonly=True)
    amount_residual = fields.Monetary(
        string="Amount Due", currency_field="currency_id", readonly=True,
    )
    days_outstanding = fields.Integer(string="Days Outstanding", readonly=True)
    days_overdue = fields.Integer(string="Days Overdue", readonly=True)
    is_overdue = fields.Boolean(string="Breaches Limit", readonly=True)
    in_current_fy = fields.Boolean(string="Current Financial Year", readonly=True)
    financial_year = fields.Char(string="Financial Year", readonly=True)
    ageing_bucket = fields.Selection(
        selection=[
            ("0_15", "0 - 15 days"),
            ("16_30", "16 - 30 days"),
            ("31_45", "31 - 45 days"),
            ("46_60", "46 - 60 days"),
            ("61_90", "61 - 90 days"),
            ("90_plus", "Over 90 days"),
        ],
        string="Ageing Bucket", readonly=True,
    )

    def _search(self, domain, *args, **kwargs):
        """Flush the source models before querying the SQL view.

        The view reads ``account_move`` and ``res_partner`` straight from the
        database, so pending ORM values - a freshly reconciled residual, a
        category just changed - have to reach the tables first.
        """
        self.env["account.move"].flush_model()
        self.env["res.partner"].flush_model()
        return super()._search(domain, *args, **kwargs)

    @property
    def _table_query(self):
        return SQL("""
            SELECT
                am.id AS id,
                am.id AS move_id,
                am.partner_id AS partner_id,
                am.company_id AS company_id,
                am.currency_id AS currency_id,
                am.invoice_date AS invoice_date,
                COALESCE(am.drkds_msme_acceptance_date, am.invoice_date)
                    AS acceptance_date,
                am.drkds_msme_due_date AS msme_due_date,
                am.drkds_msme_limit_days AS limit_days,
                am.drkds_msme_fy AS financial_year,
                rp.drkds_msme_category AS msme_category,
                rp.drkds_udyam_number AS udyam_number,
                am.amount_residual AS amount_residual,
                GREATEST(
                    CURRENT_DATE - COALESCE(
                        am.drkds_msme_acceptance_date, am.invoice_date), 0
                )::int AS days_outstanding,
                GREATEST(CURRENT_DATE - am.drkds_msme_due_date, 0)::int
                    AS days_overdue,
                (am.drkds_msme_due_date < CURRENT_DATE) AS is_overdue,
                (am.invoice_date >= CASE
                    WHEN EXTRACT(MONTH FROM CURRENT_DATE) >= 4
                        THEN MAKE_DATE(EXTRACT(YEAR FROM CURRENT_DATE)::int, 4, 1)
                    ELSE MAKE_DATE(EXTRACT(YEAR FROM CURRENT_DATE)::int - 1, 4, 1)
                 END) AS in_current_fy,
                CASE
                    WHEN CURRENT_DATE - COALESCE(
                        am.drkds_msme_acceptance_date, am.invoice_date) <= 15
                        THEN '0_15'
                    WHEN CURRENT_DATE - COALESCE(
                        am.drkds_msme_acceptance_date, am.invoice_date) <= 30
                        THEN '16_30'
                    WHEN CURRENT_DATE - COALESCE(
                        am.drkds_msme_acceptance_date, am.invoice_date) <= 45
                        THEN '31_45'
                    WHEN CURRENT_DATE - COALESCE(
                        am.drkds_msme_acceptance_date, am.invoice_date) <= 60
                        THEN '46_60'
                    WHEN CURRENT_DATE - COALESCE(
                        am.drkds_msme_acceptance_date, am.invoice_date) <= 90
                        THEN '61_90'
                    ELSE '90_plus'
                END AS ageing_bucket
            FROM account_move am
            JOIN res_partner rp ON rp.id = am.partner_id
            WHERE am.move_type = 'in_invoice'
              AND am.state = 'posted'
              AND am.drkds_msme_due_date IS NOT NULL
              AND am.amount_residual > 0
              AND COALESCE(rp.drkds_msme_registered, FALSE) IS TRUE
              AND rp.drkds_msme_category IN ('micro', 'small')
        """)
