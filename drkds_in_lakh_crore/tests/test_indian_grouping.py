from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from ..models.drkds_in_number_format import (
    INDIAN_GROUPING,
    INTERNATIONAL_GROUPING,
    group_indian,
)


@tagged("post_install", "-at_install")
class TestIndianGrouping(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Format = cls.env["drkds.in.number.format"]
        cls.lang = cls.env["res.lang"]._lang_get("en_US")

    # -- the pure helper -----------------------------------------------
    def test_grouping_ladder(self):
        """Three digits, then two, all the way up to a thousand crore."""
        expected = {
            1234: "1,234.00",
            123456: "1,23,456.00",
            12345678: "1,23,45,678.00",
            1234567890: "1,23,45,67,890.00",
        }
        for value, text in expected.items():
            self.assertEqual(group_indian(value), text, value)

    def test_short_numbers_are_untouched(self):
        for value, text in ((0, "0.00"), (7, "7.00"), (99, "99.00"), (999, "999.00")):
            self.assertEqual(group_indian(value), text, value)

    def test_first_separator_appears_at_four_digits(self):
        self.assertEqual(group_indian(999), "999.00")
        self.assertEqual(group_indian(1000), "1,000.00")

    def test_negative_numbers_keep_the_sign_attached(self):
        self.assertEqual(group_indian(-12345678), "-1,23,45,678.00")
        self.assertEqual(group_indian(-1234), "-1,234.00")

    def test_negative_zero_is_shown_as_zero(self):
        """-0.004 rounds to zero; printing '-0.00' would look like an error."""
        self.assertEqual(group_indian(-0.004), "0.00")

    def test_decimal_places(self):
        self.assertEqual(group_indian(12345678.5), "1,23,45,678.50")
        self.assertEqual(group_indian(12345678.567, digits=2), "1,23,45,678.57")
        self.assertEqual(group_indian(12345678, digits=0), "1,23,45,678")
        self.assertEqual(group_indian(12345678.9, digits=0), "1,23,45,679")

    def test_custom_separators(self):
        self.assertEqual(
            group_indian(12345678.5, thousands_sep=" ", decimal_point=","),
            "1 23 45 678,50",
        )

    def test_carry_across_a_group_boundary(self):
        """999999.999 rounds up into an extra digit and regroups."""
        self.assertEqual(group_indian(999999.999), "10,00,000.00")

    # -- the env-reachable helper --------------------------------------
    def test_model_helper_matches_the_function(self):
        self.assertEqual(self.Format.group_indian(12345678), "1,23,45,678.00")

    def test_format_in_inr(self):
        self.assertEqual(self.Format.format_in_inr(12345678), "₹ 1,23,45,678.00")
        self.assertEqual(self.Format.format_in_inr(-12345678), "-₹ 1,23,45,678.00")
        self.assertEqual(self.Format.format_in_inr(1234, symbol=False), "1,234.00")

    def test_helper_follows_the_language_separators(self):
        """The helper uses the active language's separators, not hardcoded ones."""
        self.lang.write({"thousands_sep": " ", "decimal_point": ","})
        self.env.registry.clear_cache("stable")
        self.assertEqual(
            self.env["drkds.in.number.format"].with_context(lang="en_US").group_indian(12345678),
            "1 23 45 678,00",
        )

    # -- the language switch -------------------------------------------
    def test_apply_then_restore_round_trips(self):
        original = self.lang.grouping
        self.lang.drkds_in_action_apply_indian_grouping()
        self.assertEqual(self.lang.grouping, INDIAN_GROUPING)
        self.assertTrue(self.lang.drkds_in_is_indian_grouping)

        self.lang.drkds_in_action_restore_default_grouping()
        self.assertEqual(self.lang.grouping, INTERNATIONAL_GROUPING)
        self.assertEqual(self.lang.grouping, original)
        self.assertFalse(self.lang.drkds_in_is_indian_grouping)

    def test_odoo_formats_with_the_applied_grouping(self):
        """The whole point: core formatting changes once the switch is used."""
        self.lang.drkds_in_action_apply_indian_grouping()
        self.assertEqual(
            self.lang.format("%.2f", 12345678, grouping=True), "1,23,45,678.00"
        )
        self.lang.drkds_in_action_restore_default_grouping()
        self.assertEqual(
            self.lang.format("%.2f", 12345678, grouping=True), "12,345,678.00"
        )

    def test_applied_grouping_matches_the_helper(self):
        """The language route and the utility route agree on long numbers."""
        self.lang.drkds_in_action_apply_indian_grouping()
        for value in (1234, 123456, 12345678, 1234567890):
            self.assertEqual(
                self.lang.format("%.2f", value, grouping=True),
                group_indian(value),
                value,
            )

    def test_sample_field_shows_the_current_grouping(self):
        self.lang.drkds_in_action_apply_indian_grouping()
        self.assertEqual(self.lang.drkds_in_grouping_sample, "12,34,56,789.50")
        self.lang.drkds_in_action_restore_default_grouping()
        self.assertEqual(self.lang.drkds_in_grouping_sample, "123,456,789.50")

    def test_empty_selection_is_refused(self):
        with self.assertRaises(UserError):
            self.env["res.lang"].browse().drkds_in_action_apply_indian_grouping()

    def test_install_does_not_change_any_language(self):
        """Installing the module must never reformat an existing database."""
        self.assertFalse(
            self.env["res.lang"].search([("grouping", "=", INDIAN_GROUPING)]),
            "No language may be switched to Indian grouping on install.",
        )
