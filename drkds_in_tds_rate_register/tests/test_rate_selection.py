from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import DrkdsTdsCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestRateSelection(DrkdsTdsCommon):
    """The one gap this module exists to fill: which rate the wizard picks."""

    # -- the rate map --------------------------------------------------
    def test_no_pan_vendor_gets_the_higher_rate(self):
        """The whole point: no PAN entity means the 20 per cent tax is selected."""
        bill = self._bill(self.vendor_no_pan, 100000.0, self.account_194c)
        wizard = self._wizard(bill)
        self.assertEqual(wizard.tds_deduction, "higher")
        self.assertEqual(wizard.tax_id, self.tax_194c_20)
        self.assertEqual(wizard.amount, 20000.0)
        self.assertIn("no PAN", wizard.drkds_rate_reason)

    def test_pan_vendor_gets_the_normal_rate(self):
        bill = self._bill(self.vendor_with_pan, 100000.0, self.account_194c)
        wizard = self._wizard(bill)
        self.assertEqual(wizard.tds_deduction, "normal")
        self.assertEqual(wizard.tax_id, self.tax_194c_1)
        self.assertEqual(wizard.amount, 1000.0)

    def test_lower_deduction_uses_the_lower_rate(self):
        """An explicit lower deduction choice is honoured, not overruled."""
        self.map_194c.lower_tax_id = self.tax_194c_2
        self.pan_with.tds_deduction = "lower"
        bill = self._bill(self.vendor_with_pan, 100000.0, self.account_194c)
        wizard = self._wizard(bill)
        self.assertEqual(wizard.tds_deduction, "lower")
        self.assertEqual(wizard.tax_id, self.tax_194c_2)

    def test_lower_deduction_without_a_lower_rate_proposes_nothing(self):
        """Better to leave the rate to the user than to over-deduct on a 197 certificate."""
        self.pan_with.tds_deduction = "lower"
        bill = self._bill(self.vendor_with_pan, 100000.0, self.account_194c)
        wizard = self._wizard(bill)
        self.assertFalse(wizard.tax_id)
        self.assertIn("no lower rate", wizard.drkds_rate_reason)

    def test_no_deduction_vendor_is_left_alone(self):
        self.pan_with.tds_deduction = "no"
        bill = self._bill(self.vendor_with_pan, 100000.0, self.account_194c)
        wizard = self._wizard(bill)
        self.assertFalse(wizard.tax_id)
        self.assertFalse(wizard.drkds_rate_reason)

    def test_unmapped_section_falls_back_to_core(self):
        """We only speak where we have been told the answer."""
        bill = self._bill(self.vendor_no_pan, 100000.0, self.account_194j)
        wizard = self._wizard(bill)
        self.assertFalse(wizard.drkds_rate_map_id)
        self.assertFalse(wizard.tax_id)

    def test_user_can_still_override_the_rate_by_hand(self):
        bill = self._bill(self.vendor_no_pan, 100000.0, self.account_194c)
        wizard = self._wizard(bill)
        self.assertEqual(wizard.tax_id, self.tax_194c_20)
        wizard.tax_id = self.tax_194c_2
        self.assertEqual(wizard.tax_id, self.tax_194c_2)
        self.assertEqual(wizard.amount, 2000.0)
        self.assertFalse(wizard.drkds_rate_reason)

    def test_core_history_guess_survives_for_an_unremarkable_vendor(self):
        """A vendor with a PAN and a posted history keeps the localisation's answer.

        The localisation reads the rate off the last withhold for the same PAN,
        account and section. That is a better informed answer than our default,
        so we must not tread on it.
        """
        first = self._bill(self.vendor_with_pan, 100000.0, self.account_194c)
        self._withhold(first, self.tax_194c_2)

        second = self._bill(self.vendor_with_pan, 50000.0, self.account_194c,
                            date="2026-07-11")
        follow_up = self._wizard(second)
        self.assertEqual(
            follow_up.tax_id, self.tax_194c_2,
            "The history guess of 2 per cent must not be overwritten by the mapped 1 per cent.",
        )

    def test_no_pan_still_wins_over_the_history_guess(self):
        """History cannot know a vendor has no PAN, so we override it there."""
        first = self._bill(self.vendor_no_pan, 100000.0, self.account_194c)
        self._withhold(first, self.tax_194c_1)

        second = self._bill(self.vendor_no_pan, 50000.0, self.account_194c,
                            date="2026-07-11")
        follow_up = self._wizard(second)
        self.assertEqual(follow_up.tax_id, self.tax_194c_20)

    # -- the map itself ------------------------------------------------
    def test_higher_rate_is_proposed_from_the_steepest_tax(self):
        """Section 206AA is the higher of 20 per cent and the section rate."""
        rate_map = self.env["drkds.tds.rate.map"].new({
            "section_id": self.section_194j.id,
            "company_id": self.default_company.id,
        })
        rate_map._onchange_propose_taxes()
        self.assertEqual(rate_map.higher_tax_id, self.tax_194j_20)

    def test_normal_rate_is_not_guessed_when_a_section_has_several(self):
        """194C has 1 per cent and 2 per cent: only the user knows which."""
        rate_map = self.env["drkds.tds.rate.map"].new({
            "section_id": self.section_194c.id,
            "company_id": self.default_company.id,
        })
        rate_map._onchange_propose_taxes()
        self.assertEqual(rate_map.higher_tax_id, self.tax_194c_20)
        self.assertFalse(rate_map.normal_tax_id)

    def test_a_tax_from_another_section_is_refused(self):
        with self.assertRaises(ValidationError):
            self.map_194c.normal_tax_id = self.tax_194j_10

    def test_a_section_is_mapped_once_per_company(self):
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.env["drkds.tds.rate.map"].create({
                    "section_id": self.section_194c.id,
                    "company_id": self.default_company.id,
                    "normal_tax_id": self.tax_194c_2.id,
                })

    def test_nothing_is_proposed_on_a_sale_withhold(self):
        """A customer invoice withhold is TCS territory; we stay out of it."""
        invoice = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.vendor_with_pan.id,
            "invoice_date": "2026-06-10",
            "invoice_line_ids": [Command.create({
                "name": "Sale",
                "quantity": 1.0,
                "price_unit": 100000.0,
                "tax_ids": [Command.clear()],
            })],
        })
        invoice.action_post()
        wizard = self._wizard(invoice)
        self.assertFalse(wizard.drkds_rate_map_id)
