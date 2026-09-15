from datetime import date

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestFinancialYearSequence(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.drkds_fy_start_month = "4"
        cls.Sequence = cls.env["ir.sequence"]

    def _make_sequence(self, **overrides):
        values = {
            "name": "Customer Invoice FY",
            "code": "drkds.test.fy.invoice",
            "prefix": "INV/%(range_fy)s/",
            "padding": 4,
            "company_id": self.company.id,
        }
        values.update(overrides)
        return self.Sequence.create(values)

    # -- the financial year string -------------------------------------
    def test_fy_string_on_last_day_of_year(self):
        """31 March 2026 still belongs to 2025-26."""
        self.assertEqual(self.company.drkds_fy_string(date(2026, 3, 31)), "2025-26")

    def test_fy_string_on_first_day_of_year(self):
        """1 April 2026 opens 2026-27."""
        self.assertEqual(self.company.drkds_fy_string(date(2026, 4, 1)), "2026-27")

    def test_fy_string_crosses_the_century(self):
        """The second half is two digits, so 2099-00 is produced, not 2099-100."""
        self.assertEqual(self.company.drkds_fy_string(date(2099, 6, 1)), "2099-00")

    def test_fy_short_string(self):
        self.assertEqual(self.company.drkds_fy_short_string(date(2026, 4, 1)), "2627")
        self.assertEqual(self.company.drkds_fy_short_string(date(2026, 3, 31)), "2526")

    def test_non_april_start_month_shifts(self):
        """A January start makes the financial year equal the calendar year."""
        self.company.drkds_fy_start_month = "1"
        self.assertEqual(self.company.drkds_fy_string(date(2026, 3, 31)), "2026-27")
        self.assertEqual(self.company.drkds_fy_string(date(2026, 4, 1)), "2026-27")

    def test_july_start_month_shifts(self):
        """A July start puts June in the previous financial year."""
        self.company.drkds_fy_start_month = "7"
        self.assertEqual(self.company.drkds_fy_string(date(2026, 6, 30)), "2025-26")
        self.assertEqual(self.company.drkds_fy_string(date(2026, 7, 1)), "2026-27")

    def test_fy_bounds(self):
        start, end = self.company.drkds_fy_bounds(date(2026, 12, 25))
        self.assertEqual(start, date(2026, 4, 1))
        self.assertEqual(end, date(2027, 3, 31))

    # -- token rendering -----------------------------------------------
    def test_token_renders_in_a_real_sequence_prefix(self):
        """The token is interpolated by the stock prefix machinery."""
        sequence = self._make_sequence(prefix="INV/%(fy)s/")
        prefix, suffix = sequence.with_context(
            ir_sequence_date="2026-04-01"
        )._get_prefix_suffix()
        self.assertEqual(prefix, "INV/2026-27/")
        self.assertEqual(suffix, "")

    def test_token_mixes_with_standard_odoo_tokens(self):
        """Financial year tokens do not break %(month)s and friends."""
        sequence = self._make_sequence(prefix="INV/%(fy_short)s/%(month)s/")
        prefix, __ = sequence.with_context(ir_sequence_date="2026-05-09")._get_prefix_suffix()
        self.assertEqual(prefix, "INV/2627/05/")

    def test_sequence_without_token_is_untouched(self):
        sequence = self._make_sequence(prefix="INV/%(year)s/")
        prefix, __ = sequence.with_context(ir_sequence_date="2026-04-01")._get_prefix_suffix()
        self.assertEqual(prefix, "INV/2026/")

    # -- drawing numbers -----------------------------------------------
    def test_next_by_code_numbers_within_a_financial_year(self):
        """Consecutive draws in one financial year give 0001 then 0002."""
        sequence = self._make_sequence()
        sequence.drkds_build_fy_ranges("2026-04-01", years=2)
        env = self.env["ir.sequence"].with_context(ir_sequence_date="2026-04-01")
        self.assertEqual(env.next_by_code("drkds.test.fy.invoice"), "INV/2026-27/0001")
        self.assertEqual(env.next_by_code("drkds.test.fy.invoice"), "INV/2026-27/0002")

    def test_counter_restarts_in_the_next_financial_year(self):
        """Crossing 1 April restarts the counter, it does not continue at 0003."""
        sequence = self._make_sequence()
        sequence.drkds_build_fy_ranges("2026-04-01", years=2)
        Seq = self.env["ir.sequence"]
        Seq.with_context(ir_sequence_date="2026-04-01").next_by_code("drkds.test.fy.invoice")
        Seq.with_context(ir_sequence_date="2027-03-31").next_by_code("drkds.test.fy.invoice")
        self.assertEqual(
            Seq.with_context(ir_sequence_date="2027-04-01").next_by_code("drkds.test.fy.invoice"),
            "INV/2027-28/0001",
        )

    def test_march_and_april_land_in_different_series(self):
        """31 March and 1 April draw from different financial years."""
        sequence = self._make_sequence()
        sequence.drkds_build_fy_ranges("2025-04-01", years=3)
        Seq = self.env["ir.sequence"]
        march = Seq.with_context(ir_sequence_date="2026-03-31").next_by_code("drkds.test.fy.invoice")
        april = Seq.with_context(ir_sequence_date="2026-04-01").next_by_code("drkds.test.fy.invoice")
        self.assertEqual(march, "INV/2025-26/0001")
        self.assertEqual(april, "INV/2026-27/0001")

    def test_prefix_only_does_not_restart_the_counter(self):
        """Without date ranges the number keeps climbing - the documented trap."""
        sequence = self._make_sequence(prefix="INV/%(fy)s/", use_date_range=False)
        Seq = self.env["ir.sequence"]
        Seq.with_context(ir_sequence_date="2026-04-01").next_by_code("drkds.test.fy.invoice")
        self.assertEqual(
            Seq.with_context(ir_sequence_date="2027-04-01").next_by_code("drkds.test.fy.invoice"),
            "INV/2027-28/0002",
        )

    # -- the range builder ---------------------------------------------
    def test_build_fy_ranges_covers_april_to_march(self):
        sequence = self._make_sequence()
        ranges = sequence.drkds_build_fy_ranges("2026-08-15", years=2)
        self.assertTrue(sequence.use_date_range)
        self.assertEqual(len(ranges), 2)
        bounds = sorted((r.date_from, r.date_to) for r in ranges)
        self.assertEqual(bounds[0], (date(2026, 4, 1), date(2027, 3, 31)))
        self.assertEqual(bounds[1], (date(2027, 4, 1), date(2028, 3, 31)))

    def test_build_fy_ranges_is_idempotent(self):
        sequence = self._make_sequence()
        sequence.drkds_build_fy_ranges("2026-04-01", years=2)
        sequence.drkds_build_fy_ranges("2026-04-01", years=2)
        self.assertEqual(len(sequence.date_range_ids), 2)

    def test_build_fy_ranges_follows_the_start_month(self):
        self.company.drkds_fy_start_month = "7"
        sequence = self._make_sequence()
        ranges = sequence.drkds_build_fy_ranges("2026-09-01", years=1)
        self.assertEqual((ranges.date_from, ranges.date_to), (date(2026, 7, 1), date(2027, 6, 30)))

    def test_wizard_builds_and_previews(self):
        sequence = self._make_sequence()
        wizard = self.env["drkds.fy.range.builder"].create({
            "sequence_id": sequence.id,
            "start_date": "2026-04-01",
            "year_count": 2,
        })
        self.assertEqual(wizard.preview, "INV/2026-27/0001")
        wizard.action_build()
        self.assertEqual(len(sequence.date_range_ids), 2)
