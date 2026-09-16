from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

from ..models.drkds_asset import fiscal_year_end, month_span


@tagged("post_install", "-at_install")
class TestDepreciationSchedule(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.write({
            "drkds_asset_fy_last_month": "3",
            "drkds_asset_fy_last_day": 31,
        })
        cls.Asset = cls.env["drkds.lite.asset"]
        cls.category = cls.env["drkds.lite.asset.category"].create({
            "name": "Plant and Machinery",
            "code": "PM",
            "useful_life_unit": "year",
            "useful_life_value": 3,
            "company_id": cls.company.id,
        })

    def _asset(self, **overrides):
        values = {
            "name": "Lathe",
            "category_id": self.category.id,
            "purchase_date": date(2024, 4, 1),
            "purchase_value": 30000.0,
            "salvage_value": 0.0,
            "useful_life_unit": "year",
            "useful_life_value": 3,
            "period_type": "year",
            "depreciation_start_date": date(2024, 4, 1),
            "state": "running",
        }
        values.update(overrides)
        return self.Asset.create(values)

    # -- helpers -------------------------------------------------------
    def test_month_span_counts_whole_months_as_one(self):
        """A calendar month is worth exactly one month, leap year or not."""
        self.assertEqual(month_span(date(2024, 2, 1), date(2024, 2, 29)), 1.0)
        self.assertEqual(month_span(date(2023, 2, 1), date(2023, 2, 28)), 1.0)
        self.assertEqual(month_span(date(2024, 4, 1), date(2025, 3, 31)), 12.0)

    def test_month_span_pro_rates_a_part_month(self):
        self.assertAlmostEqual(month_span(date(2024, 4, 16), date(2024, 4, 30)), 15 / 30)

    def test_fiscal_year_end_lands_on_the_next_boundary(self):
        self.assertEqual(fiscal_year_end(date(2024, 4, 1), 3, 31), date(2025, 3, 31))
        self.assertEqual(fiscal_year_end(date(2025, 3, 31), 3, 31), date(2025, 3, 31))

    def test_fiscal_year_end_clamps_a_short_month(self):
        """A 31st asked for in February falls back to the last day there is."""
        self.assertEqual(fiscal_year_end(date(2024, 1, 5), 2, 31), date(2024, 2, 29))

    # -- straight line -------------------------------------------------
    def test_three_year_schedule_on_a_round_number(self):
        """30,000 over three years from a year start is three periods of 10,000."""
        asset = self._asset()
        lines = asset.depreciation_line_ids.sorted("sequence")
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines.mapped("depreciation"), [10000.0, 10000.0, 10000.0])
        self.assertEqual(lines.mapped("opening_value"), [30000.0, 20000.0, 10000.0])
        self.assertEqual(lines.mapped("closing_value"), [20000.0, 10000.0, 0.0])
        self.assertEqual(lines[-1].date_to, date(2027, 3, 31))
        self.assertEqual(asset.depreciation_total, 30000.0)

    def test_schedule_with_salvage_closes_exactly_on_it(self):
        """A stubborn figure must still land on the salvage value to the cent."""
        asset = self._asset(purchase_value=100000.0, salvage_value=1000.0, useful_life_value=7)
        lines = asset.depreciation_line_ids.sorted("sequence")
        self.assertEqual(len(lines), 7)
        self.assertEqual(lines[-1].closing_value, 1000.0)
        self.assertAlmostEqual(sum(lines.mapped("depreciation")), 99000.0, places=2)
        # No period drifts more than a cent from an even seventh.
        for line in lines[:-1]:
            self.assertAlmostEqual(line.depreciation, 99000.0 / 7, places=2)

    def test_monthly_periods_close_on_the_salvage_value(self):
        asset = self._asset(
            period_type="month", purchase_value=10000.0, salvage_value=400.0,
            useful_life_unit="month", useful_life_value=7,
        )
        lines = asset.depreciation_line_ids.sorted("sequence")
        self.assertEqual(len(lines), 7)
        self.assertEqual(lines[0].date_from, date(2024, 4, 1))
        self.assertEqual(lines[-1].date_to, date(2024, 10, 31))
        self.assertEqual(lines[-1].closing_value, 400.0)

    def test_mid_year_start_pro_rates_first_and_last_period(self):
        """Starting on 1 October splits a three year life across four years."""
        asset = self._asset(
            purchase_date=date(2024, 10, 1),
            depreciation_start_date=date(2024, 10, 1),
            purchase_value=36000.0,
        )
        lines = asset.depreciation_line_ids.sorted("sequence")
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0].date_from, date(2024, 10, 1))
        self.assertEqual(lines[0].date_to, date(2025, 3, 31))
        self.assertEqual(lines[-1].date_to, date(2027, 9, 30))
        # Six months of a thirty-six month life on 36,000 is 6,000.
        self.assertAlmostEqual(lines[0].depreciation, 6000.0, places=2)
        self.assertAlmostEqual(lines[1].depreciation, 12000.0, places=2)
        self.assertAlmostEqual(lines[2].depreciation, 12000.0, places=2)
        self.assertAlmostEqual(lines[3].depreciation, 6000.0, places=2)
        self.assertEqual(lines[-1].closing_value, 0.0)

    def test_useful_life_in_months_is_normalised(self):
        asset = self._asset(useful_life_unit="month", useful_life_value=30)
        self.assertEqual(asset.useful_life_months, 30)
        self.assertEqual(asset.depreciation_end_date, date(2026, 9, 30))

    # -- recomputation -------------------------------------------------
    def test_changing_useful_life_rebuilds_and_leaves_no_orphans(self):
        asset = self._asset()
        old_line_ids = asset.depreciation_line_ids.ids
        self.assertEqual(len(old_line_ids), 3)

        asset.useful_life_value = 5
        new_lines = asset.depreciation_line_ids
        self.assertEqual(len(new_lines), 5)
        self.assertFalse(set(old_line_ids) & set(new_lines.ids))
        survivors = self.env["drkds.asset.depreciation.line"].search(
            [("id", "in", old_line_ids)]
        )
        self.assertFalse(survivors, "Stale depreciation lines were left behind.")
        self.assertEqual(new_lines.sorted("sequence")[-1].closing_value, 0.0)

    def test_changing_purchase_value_rebuilds_the_schedule(self):
        asset = self._asset()
        asset.purchase_value = 60000.0
        self.assertEqual(
            asset.depreciation_line_ids.sorted("sequence").mapped("depreciation"),
            [20000.0, 20000.0, 20000.0],
        )

    def test_shortening_the_life_deletes_the_surplus_periods(self):
        asset = self._asset(useful_life_value=5)
        self.assertEqual(len(asset.depreciation_line_ids), 5)
        asset.useful_life_value = 2
        self.assertEqual(len(asset.depreciation_line_ids), 2)

    # -- refusals ------------------------------------------------------
    def test_zero_useful_life_is_refused(self):
        with self.assertRaises(ValidationError):
            self._asset(useful_life_value=0)

    def test_negative_useful_life_is_refused(self):
        with self.assertRaises(ValidationError):
            self._asset(useful_life_value=-3)

    def test_salvage_above_cost_is_refused(self):
        with self.assertRaises(ValidationError):
            self._asset(purchase_value=1000.0, salvage_value=1500.0)

    def test_category_with_zero_life_is_refused(self):
        with self.assertRaises(ValidationError):
            self.env["drkds.lite.asset.category"].create({
                "name": "Nonsense",
                "useful_life_value": 0,
                "company_id": self.company.id,
            })

    # -- draft ---------------------------------------------------------
    def test_a_draft_asset_still_gets_a_schedule_to_look_at(self):
        asset = self._asset(state="draft")
        self.assertEqual(len(asset.depreciation_line_ids), 3)
        self.assertEqual(asset.value_residual, 30000.0,
                         "A draft asset is not depreciating yet.")

    def test_reference_comes_from_the_sequence(self):
        asset = self._asset()
        self.assertTrue(asset.code.startswith("FA/"))
        self.assertNotEqual(asset.code, "New")
