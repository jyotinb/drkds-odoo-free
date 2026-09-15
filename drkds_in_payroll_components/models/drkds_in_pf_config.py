from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DrkdsInPfConfig(models.Model):
    """Provident Fund (EPF/EPS) contribution rules, dated by effective-from.

    Rates shipped with the module reflect the position published for 2026:
    employee 12%, employer 12%, statutory wage ceiling INR 15,000 per month,
    of which 8.33% of the pension-ceiling wage goes to the Employees' Pension
    Scheme and the balance of the employer 12% goes to the PF account.
    Source: EPFO scheme rates as summarised by Zoho Payroll and Mercans,
    effective 2026-04-01. Rates, ceilings and the split change by
    notification; every field here is editable and the user's payroll adviser
    must confirm the numbers in force before a sheet is relied on.

    The record used for a given month is the latest one whose
    ``effective_from`` is on or before the first day of that month.
    """

    _name = "drkds.in.pf.config"
    _description = "India Provident Fund Configuration"
    _order = "effective_from desc"

    name = fields.Char(
        required=True, default="Provident Fund",
        help="Free text label, for example 'EPF from April 2026'.",
    )
    effective_from = fields.Date(
        required=True,
        help="First day from which these rates apply. A computation sheet picks "
        "the latest configuration effective on or before the month it covers.",
    )
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)

    employee_rate = fields.Float(
        string="Employee Share (%)", default=12.0, digits=(5, 3),
        help="Percentage of PF wages deducted from the employee.",
    )
    employer_rate = fields.Float(
        string="Employer Share (%)", default=12.0, digits=(5, 3),
        help="Total percentage of PF wages contributed by the employer, before "
        "the pension split below.",
    )
    wage_ceiling = fields.Float(
        string="Wage Ceiling", default=15000.0,
        help="Statutory monthly PF wage ceiling. Contributions are computed on "
        "this amount when the wage is higher, unless the contract is marked to "
        "contribute on actual wages.",
    )
    pension_rate = fields.Float(
        string="Pension Share (%)", default=8.33, digits=(5, 3),
        help="Part of the employer share diverted to the Employees' Pension "
        "Scheme. The remainder of the employer share goes to the PF account.",
    )
    pension_ceiling = fields.Float(
        string="Pension Ceiling", default=15000.0,
        help="The pension share is never computed on more than this wage, even "
        "when PF itself is computed on actual wages.",
    )
    note = fields.Text(
        string="Source Note",
        help="Record here where the rates came from and when they were checked.",
    )

    @api.constrains("employee_rate", "employer_rate", "pension_rate")
    def _check_rates(self):
        for config in self:
            if config.pension_rate > config.employer_rate:
                raise ValidationError(_(
                    "The pension share cannot be larger than the total employer share."
                ))
            for value in (config.employee_rate, config.employer_rate, config.pension_rate):
                if value < 0 or value > 100:
                    raise ValidationError(_("PF percentages must be between 0 and 100."))

    @api.constrains("wage_ceiling", "pension_ceiling")
    def _check_ceilings(self):
        for config in self:
            if config.wage_ceiling < 0 or config.pension_ceiling < 0:
                raise ValidationError(_("PF ceilings cannot be negative."))

    @api.model
    def _get_config(self, date, company=None):
        """Return the configuration in force on ``date``, or an empty recordset."""
        company = company or self.env.company
        return self.search([
            ("effective_from", "<=", date),
            ("company_id", "in", (company.id, False)),
        ], order="effective_from desc", limit=1)

    def compute(self, wage, on_actual_wage=False):
        """Split a monthly PF wage into employee, pension and employer PF shares.

        :param float wage: the monthly PF wage of the employee.
        :param bool on_actual_wage: contribute on the full wage instead of
            capping it at the statutory ceiling.
        :return: dict with ``base``, ``employee``, ``employer_pension``,
            ``employer_pf`` and ``employer_total``.
        """
        self.ensure_one()
        wage = max(wage or 0.0, 0.0)
        base = wage if on_actual_wage else min(wage, self.wage_ceiling)
        employee = base * self.employee_rate / 100.0
        employer_total = base * self.employer_rate / 100.0
        pension_base = min(base, self.pension_ceiling)
        employer_pension = pension_base * self.pension_rate / 100.0
        employer_pf = employer_total - employer_pension
        return {
            "base": base,
            "employee": employee,
            "employer_pension": employer_pension,
            "employer_pf": employer_pf,
            "employer_total": employer_total,
        }
