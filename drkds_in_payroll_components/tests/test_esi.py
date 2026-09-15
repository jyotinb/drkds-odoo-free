from datetime import date

from odoo.tests import tagged

from .common import PayrollComponentsCommon


@tagged("post_install", "-at_install")
class TestEsi(PayrollComponentsCommon):
    def test_below_threshold_is_covered(self):
        self.assertTrue(self.esi_config.is_applicable(20000.0, date(2026, 7, 1)))

    def test_exactly_at_threshold_is_covered(self):
        """21,000 is the boundary and is inside coverage, not outside it."""
        self.assertTrue(self.esi_config.is_applicable(21000.0, date(2026, 7, 1)))

    def test_above_threshold_is_not_covered(self):
        self.assertFalse(self.esi_config.is_applicable(21000.01, date(2026, 7, 1)))

    def test_contribution_periods_are_april_and_october(self):
        """April to September is one period, October to March the next."""
        self.assertTrue(self.esi_config.is_same_period(date(2026, 4, 1), date(2026, 9, 1)))
        self.assertFalse(self.esi_config.is_same_period(date(2026, 9, 1), date(2026, 10, 1)))
        self.assertTrue(self.esi_config.is_same_period(date(2026, 10, 1), date(2027, 3, 1)))
        self.assertFalse(self.esi_config.is_same_period(date(2027, 3, 1), date(2027, 4, 1)))

    def test_crossing_mid_period_continues_to_period_end(self):
        """Covered in April, raised above the threshold in July: still covered."""
        covered_since = date(2026, 4, 1)
        self.assertTrue(
            self.esi_config.is_applicable(26000.0, date(2026, 7, 1), covered_since)
        )
        self.assertTrue(
            self.esi_config.is_applicable(26000.0, date(2026, 9, 1), covered_since)
        )

    def test_coverage_stops_at_the_next_period(self):
        """The same employee drops out from the October period onwards."""
        covered_since = date(2026, 4, 1)
        self.assertFalse(
            self.esi_config.is_applicable(26000.0, date(2026, 10, 1), covered_since)
        )

    def test_contribution_is_on_full_gross_not_the_threshold(self):
        result = self.esi_config.compute(26000.0)
        self.assertAlmostEqual(result["employee"], 195.0, 2)
        self.assertAlmostEqual(result["employer"], 845.0, 2)

    def test_ordinary_contribution(self):
        result = self.esi_config.compute(20000.0)
        self.assertAlmostEqual(result["employee"], 150.0, 2)
        self.assertAlmostEqual(result["employer"], 650.0, 2)
