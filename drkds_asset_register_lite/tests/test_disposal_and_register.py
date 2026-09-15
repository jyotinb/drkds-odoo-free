from datetime import date

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDisposalAndRegister(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.write({
            "drkds_asset_fy_last_month": "3",
            "drkds_asset_fy_last_day": 31,
        })
        cls.category = cls.env["drkds.asset.category"].create({
            "name": "Vehicles",
            "code": "VEH",
            "useful_life_value": 3,
            "company_id": cls.company.id,
        })
        cls.custodian = cls.env["res.partner"].create({"name": "Site Manager"})
        cls.asset = cls.env["drkds.asset"].create({
            "name": "Delivery Van",
            "category_id": cls.category.id,
            "custodian_id": cls.custodian.id,
            "location": "Depot",
            "purchase_date": date(2024, 4, 1),
            "purchase_value": 30000.0,
            "useful_life_value": 3,
            "depreciation_start_date": date(2024, 4, 1),
            "state": "running",
        })

    # -- written down value -------------------------------------------
    def test_wdv_inside_a_period_is_pro_rated(self):
        """Halfway through the second year, half of that year is written off."""
        self.assertEqual(self.asset._wdv_as_at(date(2025, 3, 31)), 20000.0)
        self.assertEqual(self.asset._wdv_as_at(date(2025, 9, 30)), 15000.0)
        self.assertEqual(self.asset._wdv_as_at(date(2027, 3, 31)), 0.0)

    def test_wdv_before_the_start_is_the_full_cost(self):
        self.assertEqual(self.asset._wdv_as_at(date(2024, 1, 1)), 30000.0)

    # -- disposal ------------------------------------------------------
    def test_disposal_truncates_the_schedule_and_computes_the_gain(self):
        self.asset.action_dispose(disposal_date=date(2025, 9, 30), proceeds=18000.0)
        self.assertEqual(self.asset.state, "disposed")
        lines = self.asset.depreciation_line_ids.sorted("sequence")
        self.assertEqual(len(lines), 2, "The schedule must stop at the disposal.")
        self.assertEqual(lines[-1].date_to, date(2025, 9, 30))
        self.assertEqual(lines[-1].depreciation, 5000.0)
        self.assertEqual(lines[-1].closing_value, 15000.0)
        self.assertEqual(self.asset.disposal_gain, 3000.0)

    def test_disposal_below_written_down_value_is_a_loss(self):
        self.asset.action_dispose(disposal_date=date(2025, 9, 30), proceeds=12000.0)
        self.assertEqual(self.asset.disposal_gain, -3000.0)

    def test_scrapping_writes_the_whole_book_value_off(self):
        self.asset.action_dispose(disposal_date=date(2025, 9, 30), scrapped=True)
        self.assertEqual(self.asset.state, "scrapped")
        self.assertEqual(self.asset.disposal_proceeds, 0.0)
        self.assertEqual(self.asset.disposal_gain, -15000.0)

    def test_disposing_twice_is_refused(self):
        self.asset.action_dispose(disposal_date=date(2025, 9, 30), proceeds=1.0)
        with self.assertRaises(UserError):
            self.asset.action_dispose(disposal_date=date(2026, 1, 1), proceeds=1.0)

    def test_reset_to_draft_clears_the_disposal_and_restores_the_schedule(self):
        self.asset.action_dispose(disposal_date=date(2025, 9, 30), proceeds=18000.0)
        self.asset.action_set_draft()
        self.assertFalse(self.asset.disposal_date)
        self.assertEqual(self.asset.disposal_gain, 0.0)
        self.assertEqual(len(self.asset.depreciation_line_ids), 3)

    def test_disposal_wizard_previews_then_confirms(self):
        wizard = self.env["drkds.asset.disposal.wizard"].create({
            "asset_id": self.asset.id,
            "disposal_date": date(2025, 9, 30),
            "proceeds": 18000.0,
        })
        self.assertEqual(wizard.wdv_preview, 15000.0)
        self.assertEqual(wizard.gain_preview, 3000.0)
        wizard.action_confirm()
        self.assertEqual(self.asset.state, "disposed")

    def test_disposal_before_the_start_date_is_refused(self):
        wizard = self.env["drkds.asset.disposal.wizard"].create({
            "asset_id": self.asset.id,
            "disposal_date": date(2023, 1, 1),
        })
        with self.assertRaises(UserError):
            wizard.action_confirm()

    # -- workflow ------------------------------------------------------
    def test_put_into_service_only_from_draft(self):
        with self.assertRaises(UserError):
            self.asset.action_confirm()
        self.asset.action_set_draft()
        self.asset.action_confirm()
        self.assertEqual(self.asset.state, "running")

    # -- register report ----------------------------------------------
    def _wizard(self, **overrides):
        values = {"as_at_date": date(2025, 9, 30), "company_id": self.company.id}
        values.update(overrides)
        return self.env["drkds.asset.register.wizard"].create(values)

    def test_register_returns_the_written_down_value_at_that_date(self):
        rows = {row["code"]: row for row in self._wizard()._register_rows()}
        self.assertIn(self.asset.code, rows)
        row = rows[self.asset.code]
        self.assertEqual(row["purchase_value"], 30000.0)
        self.assertEqual(row["written_down_value"], 15000.0)
        self.assertEqual(row["accumulated_depreciation"], 15000.0)
        self.assertEqual(row["category_name"], "Vehicles")

    def test_register_materialises_lines_and_opens_them(self):
        wizard = self._wizard()
        action = wizard.action_view_register()
        self.assertEqual(action["res_model"], "drkds.asset.register.line")
        self.assertEqual(len(wizard.line_ids), 1)
        self.assertEqual(wizard.line_ids.written_down_value, 15000.0)
        # Running it again replaces the rows rather than doubling them.
        wizard.action_view_register()
        self.assertEqual(len(wizard.line_ids), 1)

    def test_register_excludes_a_draft_asset(self):
        self.env["drkds.asset"].create({
            "name": "Not yet in use",
            "category_id": self.category.id,
            "purchase_date": date(2024, 4, 1),
            "purchase_value": 5000.0,
            "useful_life_value": 3,
            "depreciation_start_date": date(2024, 4, 1),
        })
        codes = [row["code"] for row in self._wizard()._register_rows()]
        self.assertEqual(len(codes), 1)

    def test_register_excludes_an_asset_bought_after_the_date(self):
        rows = self._wizard(as_at_date=date(2024, 1, 1))._register_rows()
        self.assertFalse(rows)

    def test_register_filters_by_category_and_custodian(self):
        other = self.env["drkds.asset.category"].create({
            "name": "Furniture", "useful_life_value": 5, "company_id": self.company.id,
        })
        self.assertFalse(self._wizard(category_ids=[(6, 0, other.ids)])._register_rows())
        self.assertTrue(
            self._wizard(category_ids=[(6, 0, self.category.ids)])._register_rows()
        )
        stranger = self.env["res.partner"].create({"name": "Someone Else"})
        self.assertFalse(self._wizard(custodian_id=stranger.id)._register_rows())

    def test_register_freezes_a_disposed_asset_at_its_disposal_value(self):
        self.asset.action_dispose(disposal_date=date(2025, 9, 30), proceeds=18000.0)
        rows = self._wizard(as_at_date=date(2026, 3, 31), state_filter="all")._register_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["written_down_value"], 15000.0)

    def test_register_can_leave_out_fully_depreciated_assets(self):
        wizard = self._wizard(as_at_date=date(2027, 3, 31), include_zero=False)
        self.assertFalse(wizard._register_rows())
        self.assertTrue(self._wizard(as_at_date=date(2027, 3, 31))._register_rows())

    def test_register_report_renders(self):
        wizard = self._wizard()
        wizard.action_view_register()
        html = self.env["ir.actions.report"]._render_qweb_html(
            "drkds_asset_register_lite.report_asset_register", wizard.ids
        )[0]
        self.assertIn(b"Fixed Asset Register", html)
        self.assertIn(self.asset.code.encode(), html)

    # -- multi-company -------------------------------------------------
    def test_assets_are_scoped_to_their_company(self):
        other_company = self.env["res.company"].create({"name": "Second Co"})
        other_category = self.env["drkds.asset.category"].create({
            "name": "Vehicles", "useful_life_value": 3, "company_id": other_company.id,
        })
        other_asset = self.env["drkds.asset"].create({
            "name": "Other Van",
            "company_id": other_company.id,
            "category_id": other_category.id,
            "purchase_date": date(2024, 4, 1),
            "purchase_value": 9000.0,
            "useful_life_value": 3,
            "depreciation_start_date": date(2024, 4, 1),
            "state": "running",
        })
        codes = [row["code"] for row in self._wizard()._register_rows()]
        self.assertNotIn(other_asset.code, codes)
        self.assertIn(self.asset.code, codes)
