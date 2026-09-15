from datetime import date

from odoo.tests import tagged

from .common import PayrollComponentsCommon


@tagged("post_install", "-at_install")
class TestProfessionalTax(PayrollComponentsCommon):
    def test_maharashtra_bands(self):
        compute = self.Slab.compute_tax
        self.assertAlmostEqual(compute(self.maharashtra, 7000.0, date(2026, 7, 1)), 0.0, 2)
        self.assertAlmostEqual(compute(self.maharashtra, 9000.0, date(2026, 7, 1)), 175.0, 2)
        self.assertAlmostEqual(compute(self.maharashtra, 40000.0, date(2026, 7, 1)), 200.0, 2)

    def test_maharashtra_boundary_amount(self):
        """7,500 is the last rupee of the nil band, not the first of the next."""
        compute = self.Slab.compute_tax
        self.assertAlmostEqual(compute(self.maharashtra, 7500.0, date(2026, 7, 1)), 0.0, 2)
        self.assertAlmostEqual(compute(self.maharashtra, 10000.0, date(2026, 7, 1)), 175.0, 2)

    def test_maharashtra_special_month(self):
        """February carries 300 instead of 200 so the year reaches the cap."""
        self.assertAlmostEqual(
            self.Slab.compute_tax(self.maharashtra, 40000.0, date(2027, 2, 1)), 300.0, 2,
        )

    def test_special_month_only_applies_to_its_own_band(self):
        """The nil band has no special month, so February changes nothing."""
        self.assertAlmostEqual(
            self.Slab.compute_tax(self.maharashtra, 7000.0, date(2027, 2, 1)), 0.0, 2,
        )

    def test_west_bengal_bands_and_boundary(self):
        compute = self.Slab.compute_tax
        day = date(2026, 7, 1)
        self.assertAlmostEqual(compute(self.west_bengal, 10000.0, day), 0.0, 2)
        self.assertAlmostEqual(compute(self.west_bengal, 15000.0, day), 110.0, 2)
        self.assertAlmostEqual(compute(self.west_bengal, 25000.0, day), 130.0, 2)
        self.assertAlmostEqual(compute(self.west_bengal, 40000.0, day), 150.0, 2)
        self.assertAlmostEqual(compute(self.west_bengal, 45000.0, day), 200.0, 2)

    def test_west_bengal_has_no_special_month(self):
        """Same wage, two states, different February treatment."""
        self.assertAlmostEqual(
            self.Slab.compute_tax(self.west_bengal, 45000.0, date(2027, 2, 1)), 200.0, 2,
        )
        self.assertAlmostEqual(
            self.Slab.compute_tax(self.karnataka, 45000.0, date(2027, 2, 1)), 300.0, 2,
        )

    def test_state_without_a_slab_table_returns_zero(self):
        gone = self.env.ref("base.state_in_ga")
        self.assertAlmostEqual(
            self.Slab.compute_tax(gone, 45000.0, date(2026, 7, 1)), 0.0, 2,
        )

    def test_no_state_returns_zero(self):
        self.assertAlmostEqual(
            self.Slab.compute_tax(self.env["res.country.state"], 45000.0, date(2026, 7, 1)),
            0.0, 2,
        )

    def test_a_later_table_supersedes_the_earlier_one(self):
        """Effective-from dating means a revision does not overwrite history."""
        self.Slab.create({
            "state_id": self.west_bengal.id,
            "effective_from": "2026-08-01",
            "amount_from": 0.0,
            "amount_to": 0.0,
            "monthly_tax": 250.0,
        })
        self.assertAlmostEqual(
            self.Slab.compute_tax(self.west_bengal, 45000.0, date(2026, 7, 1)), 200.0, 2,
        )
        self.assertAlmostEqual(
            self.Slab.compute_tax(self.west_bengal, 45000.0, date(2026, 9, 1)), 250.0, 2,
        )
