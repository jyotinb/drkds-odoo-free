from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DrkdsInEsiConfig(models.Model):
    """Employees' State Insurance contribution rules, dated by effective-from.

    Rates shipped with the module reflect the position published for 2026:
    employee 0.75%, employer 3.25% of gross wages, with mandatory coverage for
    gross wages up to INR 21,000 per month (INR 25,000 for employees with a
    disability). Contribution periods run April-September and October-March;
    an employee whose wage crosses the threshold inside a period stays covered
    until the period ends. Source: ESIC rates unchanged since July 2019, as
    summarised by Tally and HROne, checked 2026-09-15. These change by
    notification and must be confirmed by the user's payroll adviser.
    """

    _name = "drkds.in.esi.config"
    _description = "India ESI Configuration"
    _order = "effective_from desc"

    name = fields.Char(required=True, default="ESI")
    effective_from = fields.Date(
        required=True,
        help="First day from which these rates apply.",
    )
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)

    employee_rate = fields.Float(
        string="Employee Share (%)", default=0.75, digits=(5, 3),
    )
    employer_rate = fields.Float(
        string="Employer Share (%)", default=3.25, digits=(5, 3),
    )
    wage_threshold = fields.Float(
        string="Gross Wage Threshold", default=21000.0,
        help="Employees whose monthly gross wage is at or below this amount are "
        "covered. Crossing it mid-period does not end coverage until the "
        "contribution period ends.",
    )
    period_one_start_month = fields.Integer(
        string="First Period Starts In Month", default=4,
        help="Month number on which the first contribution period of the year "
        "starts. In India this is April, so the periods are April-September "
        "and October-March.",
    )
    period_length = fields.Integer(
        string="Contribution Period Length (Months)", default=6,
    )
    note = fields.Text(string="Source Note")

    @api.constrains("employee_rate", "employer_rate", "wage_threshold")
    def _check_values(self):
        for config in self:
            if not 0 <= config.employee_rate <= 100 or not 0 <= config.employer_rate <= 100:
                raise ValidationError(_("ESI percentages must be between 0 and 100."))
            if config.wage_threshold < 0:
                raise ValidationError(_("The ESI wage threshold cannot be negative."))

    @api.constrains("period_one_start_month", "period_length")
    def _check_period(self):
        for config in self:
            if not 1 <= config.period_one_start_month <= 12:
                raise ValidationError(_("The period start month must be between 1 and 12."))
            if config.period_length < 1 or 12 % config.period_length:
                raise ValidationError(_(
                    "The contribution period length must divide the year evenly."
                ))

    @api.model
    def _get_config(self, date, company=None):
        """Return the configuration in force on ``date``, or an empty recordset."""
        company = company or self.env.company
        return self.search([
            ("effective_from", "<=", date),
            ("company_id", "in", (company.id, False)),
        ], order="effective_from desc", limit=1)

    def contribution_period(self, date):
        """Return the (first month, last month) index pair covering ``date``.

        Months are returned as absolute month numbers ``year * 12 + month - 1``
        so a period that straddles a calendar year is still a simple range.
        """
        self.ensure_one()
        index = date.year * 12 + date.month - 1
        offset = (index - (self.period_one_start_month - 1)) % self.period_length
        first = index - offset
        return first, first + self.period_length - 1

    def is_same_period(self, date_a, date_b):
        """True when both dates fall in the same ESI contribution period."""
        self.ensure_one()
        return self.contribution_period(date_a) == self.contribution_period(date_b)

    def is_applicable(self, gross_wage, date, covered_since=None):
        """Decide whether ESI is deducted for a month.

        :param float gross_wage: the gross wage of the month being computed.
        :param date: first day of the month being computed.
        :param covered_since: the date on which the employee last became
            covered, if any. When the wage now exceeds the threshold but that
            date falls in the same contribution period, coverage continues to
            the end of the period.
        """
        self.ensure_one()
        if (gross_wage or 0.0) <= self.wage_threshold:
            return True
        if covered_since and self.is_same_period(covered_since, date):
            return True
        return False

    def compute(self, gross_wage):
        """Return the employee and employer ESI shares on a gross wage.

        Contributions are computed on the full gross wage: unlike PF there is
        no ceiling, the threshold only decides who is covered.
        """
        self.ensure_one()
        gross_wage = max(gross_wage or 0.0, 0.0)
        return {
            "base": gross_wage,
            "employee": gross_wage * self.employee_rate / 100.0,
            "employer": gross_wage * self.employer_rate / 100.0,
        }
