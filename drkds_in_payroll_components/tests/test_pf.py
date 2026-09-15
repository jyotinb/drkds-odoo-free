from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import PayrollComponentsCommon


@tagged("post_install", "-at_install")
class TestProvidentFund(PayrollComponentsCommon):
    def test_wage_below_ceiling_uses_actual_wage(self):
        """Under the ceiling there is nothing to cap, so the wage is the base."""
        result = self.pf_config.compute(12000.0)
        self.assertAlmostEqual(result["base"], 12000.0, 2)
        self.assertAlmostEqual(result["employee"], 1440.0, 2)
        self.assertAlmostEqual(result["employer_total"], 1440.0, 2)

    def test_wage_above_ceiling_is_capped_by_default(self):
        """A 30,000 wage still contributes on 15,000 unless told otherwise."""
        result = self.pf_config.compute(30000.0)
        self.assertAlmostEqual(result["base"], 15000.0, 2)
        self.assertAlmostEqual(result["employee"], 1800.0, 2)
        self.assertAlmostEqual(result["employer_total"], 1800.0, 2)

    def test_wage_above_ceiling_on_actual_wage(self):
        """With the option on, PF is computed on the full 30,000."""
        result = self.pf_config.compute(30000.0, on_actual_wage=True)
        self.assertAlmostEqual(result["base"], 30000.0, 2)
        self.assertAlmostEqual(result["employee"], 3600.0, 2)
        self.assertAlmostEqual(result["employer_total"], 3600.0, 2)

    def test_employer_split_at_the_ceiling(self):
        """8.33% of 15,000 to pension, the balance of the 12% to the fund."""
        result = self.pf_config.compute(15000.0)
        self.assertAlmostEqual(result["employer_pension"], 1249.50, 2)
        self.assertAlmostEqual(result["employer_pf"], 1800.0 - 1249.50, 2)
        self.assertAlmostEqual(
            result["employer_pf"] + result["employer_pension"],
            result["employer_total"], 2,
        )

    def test_pension_share_never_exceeds_its_own_ceiling(self):
        """On actual wages the pension share stays pinned to the pension ceiling."""
        result = self.pf_config.compute(30000.0, on_actual_wage=True)
        self.assertAlmostEqual(result["employer_pension"], 1249.50, 2)
        self.assertAlmostEqual(result["employer_pf"], 3600.0 - 1249.50, 2)

    def test_split_always_adds_back_to_the_employer_share(self):
        for wage in (5000.0, 15000.0, 15000.01, 90000.0):
            for actual in (False, True):
                result = self.pf_config.compute(wage, actual)
                self.assertAlmostEqual(
                    result["employer_pf"] + result["employer_pension"],
                    result["employer_total"], 2,
                    "split does not reconcile at %s (actual=%s)" % (wage, actual),
                )

    def test_pension_rate_cannot_exceed_employer_rate(self):
        with self.assertRaises(ValidationError):
            self.pf_config.copy({"pension_rate": 20.0})

    def test_rates_are_editable_not_hardcoded(self):
        """Changing the record changes the answer; no number lives in the code."""
        config = self.pf_config.copy({"employee_rate": 10.0, "wage_ceiling": 21000.0})
        result = config.compute(30000.0)
        self.assertAlmostEqual(result["base"], 21000.0, 2)
        self.assertAlmostEqual(result["employee"], 2100.0, 2)
