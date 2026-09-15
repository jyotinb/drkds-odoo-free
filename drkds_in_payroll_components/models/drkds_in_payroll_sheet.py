from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

MONTH_SELECTION = [
    ("1", "January"), ("2", "February"), ("3", "March"), ("4", "April"),
    ("5", "May"), ("6", "June"), ("7", "July"), ("8", "August"),
    ("9", "September"), ("10", "October"), ("11", "November"), ("12", "December"),
]


class DrkdsInPayrollSheet(models.Model):
    """A monthly working paper for Indian statutory payroll contributions.

    Pick a month and a set of employees, compute PF, ESI and professional tax
    for each of them, review the totals and confirm the sheet so the numbers
    are kept as they stood. This is deliberately a working paper and nothing
    more: it does not produce payslips, it does not post journal entries and it
    does not file anything with any portal.
    """

    _name = "drkds.in.payroll.sheet"
    _description = "India Payroll Components Sheet"
    _order = "year desc, month desc, id desc"
    _inherit = ["mail.thread"]

    name = fields.Char(
        compute="_compute_name", store=True, readonly=True,
    )
    year = fields.Integer(
        required=True, default=lambda self: fields.Date.context_today(self).year,
    )
    month = fields.Selection(
        MONTH_SELECTION, required=True,
        default=lambda self: str(fields.Date.context_today(self).month),
    )
    date_start = fields.Date(
        string="Month Start", compute="_compute_dates", store=True,
    )
    date_end = fields.Date(
        string="Month End", compute="_compute_dates", store=True,
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)
    employee_ids = fields.Many2many(
        "hr.employee", string="Employees",
        help="Employees to include. Leave empty and use Compute to pull in "
        "every employee of the company that has at least one component "
        "switched on.",
    )
    line_ids = fields.One2many(
        "drkds.in.payroll.sheet.line", "sheet_id", string="Lines",
    )
    state = fields.Selection(
        [("draft", "Draft"), ("confirmed", "Confirmed")],
        default="draft", required=True, tracking=True,
    )
    note = fields.Text(string="Review Notes")

    amount_pf_employee = fields.Monetary(compute="_compute_totals", store=True, string="PF Employee")
    amount_pf_employer = fields.Monetary(compute="_compute_totals", store=True, string="PF Employer")
    amount_esi_employee = fields.Monetary(compute="_compute_totals", store=True, string="ESI Employee")
    amount_esi_employer = fields.Monetary(compute="_compute_totals", store=True, string="ESI Employer")
    amount_professional_tax = fields.Monetary(compute="_compute_totals", store=True, string="Professional Tax")
    amount_employee_total = fields.Monetary(compute="_compute_totals", store=True, string="Total Deducted")
    amount_employer_total = fields.Monetary(compute="_compute_totals", store=True, string="Total Employer Cost")
    amount_total = fields.Monetary(compute="_compute_totals", store=True, string="Grand Total")

    _period_uniq = models.Constraint(
        "unique(company_id, year, month)",
        "A statutory components sheet already exists for that company and month.",
    )

    @api.depends("year", "month")
    def _compute_dates(self):
        for sheet in self:
            if sheet.year and sheet.month:
                start = date(sheet.year, int(sheet.month), 1)
                sheet.date_start = start
                sheet.date_end = start + relativedelta(months=1, days=-1)
            else:
                sheet.date_start = sheet.date_end = False

    @api.depends("year", "month", "company_id")
    def _compute_name(self):
        months = dict(MONTH_SELECTION)
        for sheet in self:
            if sheet.year and sheet.month:
                sheet.name = "%s %s" % (months.get(sheet.month, ""), sheet.year)
            else:
                sheet.name = _("New Sheet")

    @api.depends(
        "line_ids.pf_employee", "line_ids.pf_employer_pf",
        "line_ids.pf_employer_pension", "line_ids.esi_employee",
        "line_ids.esi_employer", "line_ids.professional_tax",
    )
    def _compute_totals(self):
        for sheet in self:
            lines = sheet.line_ids
            sheet.amount_pf_employee = sum(lines.mapped("pf_employee"))
            sheet.amount_pf_employer = sum(lines.mapped("pf_employer_total"))
            sheet.amount_esi_employee = sum(lines.mapped("esi_employee"))
            sheet.amount_esi_employer = sum(lines.mapped("esi_employer"))
            sheet.amount_professional_tax = sum(lines.mapped("professional_tax"))
            sheet.amount_employee_total = sum(lines.mapped("total_employee"))
            sheet.amount_employer_total = sum(lines.mapped("total_employer"))
            sheet.amount_total = sheet.amount_employee_total + sheet.amount_employer_total

    def _candidate_employees(self):
        """Employees to compute: the chosen ones, else everyone with a component on."""
        self.ensure_one()
        if self.employee_ids:
            return self.employee_ids
        return self.env["hr.employee"].search([
            ("company_id", "=", self.company_id.id),
            "|", "|",
            ("drkds_in_pf_applicable", "=", True),
            ("drkds_in_esi_applicable", "=", True),
            ("drkds_in_pt_applicable", "=", True),
        ])

    def action_compute(self):
        """Rebuild the lines of a draft sheet from the current contract data."""
        for sheet in self:
            if sheet.state != "draft":
                raise UserError(_("Reset the sheet to draft before recomputing it."))
            sheet.line_ids.unlink()
            values = [
                dict(sheet._prepare_line(employee), sheet_id=sheet.id)
                for employee in sheet._candidate_employees()
            ]
            if values:
                self.env["drkds.in.payroll.sheet.line"].create(values)
        return True

    def _prepare_line(self, employee):
        """Compute every statutory component for one employee for this month."""
        self.ensure_one()
        day = self.date_start
        company = self.company_id
        wage = employee.wage or 0.0
        values = {
            "employee_id": employee.id,
            "wage": wage,
            "pf_employee": 0.0,
            "pf_employer_pf": 0.0,
            "pf_employer_pension": 0.0,
            "esi_employee": 0.0,
            "esi_employer": 0.0,
            "professional_tax": 0.0,
            "esi_applied": False,
        }

        if employee.drkds_in_pf_applicable:
            pf_config = self.env["drkds.in.pf.config"]._get_config(day, company)
            if pf_config:
                pf = pf_config.compute(wage, employee.drkds_in_pf_on_actual_wage)
                values.update({
                    "pf_employee": pf["employee"],
                    "pf_employer_pf": pf["employer_pf"],
                    "pf_employer_pension": pf["employer_pension"],
                })

        if employee.drkds_in_esi_applicable:
            esi_config = self.env["drkds.in.esi.config"]._get_config(day, company)
            if esi_config and esi_config.is_applicable(
                wage, day, employee.drkds_in_esi_covered_since,
            ):
                esi = esi_config.compute(wage)
                values.update({
                    "esi_employee": esi["employee"],
                    "esi_employer": esi["employer"],
                    "esi_applied": True,
                })

        if employee.drkds_in_pt_applicable:
            values["professional_tax"] = self.env["drkds.in.pt.slab"].compute_tax(
                employee.drkds_in_pt_state_id, wage, day,
            )
        return values

    def action_confirm(self):
        for sheet in self:
            if not sheet.line_ids:
                raise UserError(_("Compute the sheet before confirming it."))
            sheet.state = "confirmed"
        return True

    def action_draft(self):
        self.state = "draft"
        return True


class DrkdsInPayrollSheetLine(models.Model):
    """One employee's statutory contributions for the month of its sheet."""

    _name = "drkds.in.payroll.sheet.line"
    _description = "India Payroll Components Sheet Line"
    _order = "sheet_id, employee_id"

    sheet_id = fields.Many2one(
        "drkds.in.payroll.sheet", required=True, ondelete="cascade", index=True,
    )
    employee_id = fields.Many2one("hr.employee", required=True, index=True)
    currency_id = fields.Many2one(related="sheet_id.currency_id", readonly=True)

    wage = fields.Monetary(string="Monthly Wage")
    pf_employee = fields.Monetary(string="PF Employee")
    pf_employer_pf = fields.Monetary(string="PF Employer (Fund)")
    pf_employer_pension = fields.Monetary(string="PF Employer (Pension)")
    pf_employer_total = fields.Monetary(
        string="PF Employer", compute="_compute_pf_employer_total", store=True,
    )
    esi_employee = fields.Monetary(string="ESI Employee")
    esi_employer = fields.Monetary(string="ESI Employer")
    esi_applied = fields.Boolean(
        string="ESI Covered",
        help="Ticked when ESI was deducted for this month, including where the "
        "wage is above the threshold but the contribution period has not ended.",
    )
    professional_tax = fields.Monetary(string="Professional Tax")

    total_employee = fields.Monetary(
        string="Total Deducted", compute="_compute_totals", store=True,
    )
    total_employer = fields.Monetary(
        string="Employer Cost", compute="_compute_totals", store=True,
    )

    _employee_uniq = models.Constraint(
        "unique(sheet_id, employee_id)",
        "An employee may only appear once on a statutory components sheet.",
    )

    @api.depends("pf_employer_pf", "pf_employer_pension")
    def _compute_pf_employer_total(self):
        for line in self:
            line.pf_employer_total = line.pf_employer_pf + line.pf_employer_pension

    @api.depends(
        "pf_employee", "esi_employee", "professional_tax",
        "pf_employer_pf", "pf_employer_pension", "esi_employer",
    )
    def _compute_totals(self):
        for line in self:
            line.total_employee = (
                line.pf_employee + line.esi_employee + line.professional_tax
            )
            line.total_employer = (
                line.pf_employer_pf + line.pf_employer_pension + line.esi_employer
            )
