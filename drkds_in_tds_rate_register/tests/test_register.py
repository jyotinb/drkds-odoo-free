from odoo.tests import tagged

from .common import DrkdsTdsCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestRegisterAndYtd(DrkdsTdsCommon):
    """The two reports: one row per deduction, and the running yearly total."""

    # -- register ------------------------------------------------------
    def test_register_row_matches_the_withhold(self):
        bill = self._bill(self.vendor_with_pan, 100000.0, self.account_194c)
        self._withhold(bill)
        row = self.env["drkds.tds.register"].search([("move_id", "=", bill.id)])
        self.assertEqual(len(row), 1)
        self.assertEqual(row.partner_id, self.vendor_with_pan)
        self.assertEqual(row.pan, "AAAPL1234C")
        self.assertEqual(row.section_id, self.section_194c)
        self.assertEqual(row.base_amount, 100000.0)
        self.assertEqual(row.rate, 1.0)
        self.assertEqual(row.tds_amount, 1000.0)
        self.assertEqual(row.state, "posted")
        self.assertFalse(row.no_pan)

    def test_register_totals_match_the_withholds(self):
        bills = self.env["account.move"]
        for partner, amount, date in (
            (self.vendor_with_pan, 100000.0, "2026-06-10"),
            (self.vendor_no_pan, 50000.0, "2026-11-04"),
            (self.vendor_with_pan, 40000.0, "2027-02-02"),
        ):
            bill = self._bill(partner, amount, self.account_194c, date=date)
            self._withhold(bill)
            bills |= bill
        rows = self.env["drkds.tds.register"].search([("move_id", "in", bills.ids)])
        self.assertEqual(len(rows), 3)
        self.assertEqual(sum(rows.mapped("base_amount")), 190000.0)
        # 1% of 1,00,000 + 20% of 50,000 + 1% of 40,000
        self.assertEqual(sum(rows.mapped("tds_amount")), 1000.0 + 10000.0 + 400.0)
        self.assertEqual(
            sum(rows.mapped("tds_amount")),
            sum(bills.mapped("l10n_in_total_withholding_amount")),
        )

    def test_register_flags_a_vendor_without_pan(self):
        bill = self._bill(self.vendor_no_pan, 100000.0, self.account_194c)
        self._withhold(bill)
        row = self.env["drkds.tds.register"].search([("move_id", "=", bill.id)])
        self.assertTrue(row.no_pan)
        self.assertFalse(row.pan)
        self.assertEqual(row.rate, 20.0)

    def test_register_quarters_and_financial_year(self):
        expected = {"2026-06-10": "Q1", "2026-08-14": "Q2",
                    "2026-12-01": "Q3", "2027-03-05": "Q4"}
        rows_by_quarter = {}
        for date in expected:
            bill = self._bill(self.vendor_with_pan, 60000.0, self.account_194c, date=date)
            self._withhold(bill, date=date)
            row = self.env["drkds.tds.register"].search([("move_id", "=", bill.id)])
            rows_by_quarter[date] = row
        for date, quarter in expected.items():
            self.assertEqual(rows_by_quarter[date].quarter, quarter, date)
            self.assertEqual(rows_by_quarter[date].financial_year, "2026-27", date)

    def test_bill_without_a_withhold_is_not_in_the_register(self):
        bill = self._bill(self.vendor_with_pan, 100000.0, self.account_194c)
        self.assertFalse(self.env["drkds.tds.register"].search([("move_id", "=", bill.id)]))

    def test_register_groups_by_section(self):
        self._withhold(self._bill(self.vendor_with_pan, 100000.0, self.account_194c))
        groups = self.env["drkds.tds.register"]._read_group(
            [("partner_id", "=", self.vendor_with_pan.id)],
            groupby=["section_id"], aggregates=["tds_amount:sum"],
        )
        self.assertEqual(len(groups), 1)
        section, total = groups[0]
        self.assertEqual(section, self.section_194c)
        self.assertEqual(total, 1000.0)

    # -- year to date --------------------------------------------------
    def test_ytd_sums_the_bills_of_the_year(self):
        self._bill(self.vendor_with_pan, 60000.0, self.account_194c, date="2026-06-10")
        self._bill(self.vendor_with_pan, 40000.0, self.account_194c, date="2026-09-10")
        row = self.env["drkds.tds.ytd"].search([
            ("partner_id", "=", self.vendor_with_pan.id),
            ("section_id", "=", self.section_194c.id),
            ("financial_year", "=", "2026-27"),
        ])
        self.assertEqual(len(row), 1)
        self.assertEqual(row.base_amount, 100000.0)
        self.assertEqual(row.bill_count, 2)
        self.assertEqual(row.pan_entity_id, self.pan_with)

    def test_ytd_splits_on_1_april(self):
        self._bill(self.vendor_with_pan, 60000.0, self.account_194c, date="2027-03-20")
        self._bill(self.vendor_with_pan, 40000.0, self.account_194c, date="2027-04-05")
        years = self.env["drkds.tds.ytd"].search([
            ("partner_id", "=", self.vendor_with_pan.id),
            ("section_id", "=", self.section_194c.id),
        ])
        self.assertEqual(
            {row.financial_year: row.base_amount for row in years},
            {"2026-27": 60000.0, "2027-28": 40000.0},
        )

    def test_ytd_flags_a_crossed_annual_threshold(self):
        limit = self.section_194c.aggregate_limit
        self.assertTrue(self.section_194c.is_aggregate_limit, "194C should carry an annual limit")
        self._bill(self.vendor_with_pan, limit + 5000.0, self.account_194c)
        row = self.env["drkds.tds.ytd"].search([
            ("partner_id", "=", self.vendor_with_pan.id),
            ("section_id", "=", self.section_194c.id),
            ("financial_year", "=", "2026-27"),
        ])
        self.assertTrue(row.over_threshold)
        self.assertEqual(row.aggregate_limit, limit)
        found = self.env["drkds.tds.ytd"].search([
            ("over_threshold", "=", True),
            ("partner_id", "=", self.vendor_with_pan.id),
        ])
        self.assertIn(row, found)

    def test_ytd_shows_what_has_been_deducted(self):
        bill = self._bill(self.vendor_with_pan, 100000.0, self.account_194c)
        self._bill(self.vendor_with_pan, 50000.0, self.account_194c, date="2026-07-01")
        self._withhold(bill)
        row = self.env["drkds.tds.ytd"].search([
            ("partner_id", "=", self.vendor_with_pan.id),
            ("section_id", "=", self.section_194c.id),
            ("financial_year", "=", "2026-27"),
        ])
        self.assertEqual(row.base_amount, 150000.0)
        self.assertEqual(row.deducted_amount, 1000.0)

    def test_ytd_ignores_a_draft_bill(self):
        self._bill(self.vendor_with_pan, 100000.0, self.account_194c, post=False)
        self.assertFalse(self.env["drkds.tds.ytd"].search([
            ("partner_id", "=", self.vendor_with_pan.id),
            ("section_id", "=", self.section_194c.id),
        ]))

    def test_ytd_opens_the_bills_behind_a_row(self):
        self._bill(self.vendor_with_pan, 100000.0, self.account_194c)
        row = self.env["drkds.tds.ytd"].search([
            ("partner_id", "=", self.vendor_with_pan.id),
            ("section_id", "=", self.section_194c.id),
        ])
        action = row.action_open_bills()
        self.assertEqual(action["res_model"], "account.move")
        self.assertTrue(self.env["account.move"].search(action["domain"]))
