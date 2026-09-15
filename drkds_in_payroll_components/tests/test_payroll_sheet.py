from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import PayrollComponentsCommon


@tagged("post_install", "-at_install")
class TestPayrollSheet(PayrollComponentsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.all_on = cls._employee(
            "All Components", 18000.0,
            drkds_in_pf_applicable=True,
            drkds_in_esi_applicable=True,
            drkds_in_esi_covered_since="2026-04-01",
            drkds_in_pt_applicable=True,
            drkds_in_pt_state_id=cls.maharashtra.id,
            drkds_in_uan="100 200 300 400",
        )
        cls.pf_only = cls._employee(
            "PF Only", 40000.0,
            drkds_in_pf_applicable=True,
            drkds_in_esi_applicable=False,
            drkds_in_pt_applicable=False,
        )
        cls.sheet = cls.env["drkds.in.payroll.sheet"].create({
            "year": 2026,
            "month": "7",
            "employee_ids": [(6, 0, (cls.all_on + cls.pf_only).ids)],
        })

    def _line(self, employee):
        return self.sheet.line_ids.filtered(lambda line: line.employee_id == employee)

    def test_period_dates_and_name(self):
        self.assertEqual(str(self.sheet.date_start), "2026-07-01")
        self.assertEqual(str(self.sheet.date_end), "2026-07-31")
        self.assertEqual(self.sheet.name, "July 2026")

    def test_compute_builds_one_line_per_employee(self):
        self.sheet.action_compute()
        self.assertEqual(len(self.sheet.line_ids), 2)

    def test_all_components_computed_for_a_covered_employee(self):
        self.sheet.action_compute()
        line = self._line(self.all_on)
        # PF on the 15,000 ceiling, not on the 18,000 wage.
        self.assertAlmostEqual(line.pf_employee, 1800.0, 2)
        self.assertAlmostEqual(line.pf_employer_pension, 1249.50, 2)
        self.assertAlmostEqual(line.pf_employer_pf, 550.50, 2)
        # ESI on the full gross, under the 21,000 threshold.
        self.assertTrue(line.esi_applied)
        self.assertAlmostEqual(line.esi_employee, 135.0, 2)
        self.assertAlmostEqual(line.esi_employer, 585.0, 2)
        # Maharashtra, ordinary month.
        self.assertAlmostEqual(line.professional_tax, 200.0, 2)

    def test_switched_off_components_are_zero(self):
        """ESI and professional tax off on the contract means zero, not a default."""
        self.sheet.action_compute()
        line = self._line(self.pf_only)
        self.assertFalse(line.esi_applied)
        self.assertAlmostEqual(line.esi_employee, 0.0, 2)
        self.assertAlmostEqual(line.esi_employer, 0.0, 2)
        self.assertAlmostEqual(line.professional_tax, 0.0, 2)
        self.assertAlmostEqual(line.pf_employee, 1800.0, 2)

    def test_employee_with_every_component_off_computes_to_nothing(self):
        silent = self._employee("Nothing Applies", 50000.0)
        self.sheet.employee_ids = [(4, silent.id)]
        self.sheet.action_compute()
        line = self._line(silent)
        self.assertAlmostEqual(line.total_employee, 0.0, 2)
        self.assertAlmostEqual(line.total_employer, 0.0, 2)

    def test_line_totals_add_up(self):
        self.sheet.action_compute()
        for line in self.sheet.line_ids:
            self.assertAlmostEqual(
                line.total_employee,
                line.pf_employee + line.esi_employee + line.professional_tax, 2,
            )
            self.assertAlmostEqual(
                line.total_employer,
                line.pf_employer_pf + line.pf_employer_pension + line.esi_employer, 2,
            )

    def test_sheet_total_equals_the_sum_of_its_lines(self):
        self.sheet.action_compute()
        lines = self.sheet.line_ids
        self.assertAlmostEqual(
            self.sheet.amount_employee_total, sum(lines.mapped("total_employee")), 2,
        )
        self.assertAlmostEqual(
            self.sheet.amount_employer_total, sum(lines.mapped("total_employer")), 2,
        )
        self.assertAlmostEqual(
            self.sheet.amount_total,
            self.sheet.amount_employee_total + self.sheet.amount_employer_total, 2,
        )
        self.assertAlmostEqual(
            self.sheet.amount_professional_tax, sum(lines.mapped("professional_tax")), 2,
        )

    def test_esi_continues_when_the_wage_crosses_mid_period(self):
        """A raise to 26,000 in July does not end coverage that started in April."""
        self.all_on.wage = 26000.0
        self.sheet.action_compute()
        line = self._line(self.all_on)
        self.assertTrue(line.esi_applied)
        self.assertAlmostEqual(line.esi_employee, 195.0, 2)

    def test_esi_ends_in_the_following_period(self):
        self.all_on.wage = 26000.0
        october = self.env["drkds.in.payroll.sheet"].create({
            "year": 2026, "month": "10",
            "employee_ids": [(6, 0, self.all_on.ids)],
        })
        october.action_compute()
        self.assertFalse(october.line_ids.esi_applied)
        self.assertAlmostEqual(october.line_ids.esi_employee, 0.0, 2)

    def test_february_special_month_reaches_the_sheet(self):
        february = self.env["drkds.in.payroll.sheet"].create({
            "year": 2027, "month": "2",
            "employee_ids": [(6, 0, self.all_on.ids)],
        })
        february.action_compute()
        self.assertAlmostEqual(february.line_ids.professional_tax, 300.0, 2)

    def test_confirm_requires_lines_and_locks_recompute(self):
        with self.assertRaises(UserError):
            self.sheet.action_confirm()
        self.sheet.action_compute()
        self.sheet.action_confirm()
        self.assertEqual(self.sheet.state, "confirmed")
        with self.assertRaises(UserError):
            self.sheet.action_compute()
        self.sheet.action_draft()
        self.sheet.action_compute()

    def test_recompute_replaces_rather_than_appends(self):
        self.sheet.action_compute()
        self.sheet.action_compute()
        self.assertEqual(len(self.sheet.line_ids), 2)

    def test_no_aadhaar_field_exists_anywhere(self):
        """The repo forbids storing Aadhaar; assert no field sneaks one in."""
        for model in ("hr.version", "hr.employee", "drkds.in.payroll.sheet.line"):
            for name in self.env[model]._fields:
                self.assertNotIn("aadhaar", name.lower())
                self.assertNotIn("aadhar", name.lower())
