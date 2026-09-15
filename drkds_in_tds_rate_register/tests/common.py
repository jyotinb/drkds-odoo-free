from odoo import Command
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


class DrkdsTdsCommon(L10nInTestInvoicingCommon):
    """A company on the Indian chart with two sections tagged and mapped."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ChartTemplate = cls.env["account.chart.template"]
        cls.section_194c = cls.env.ref("l10n_in.tds_section_194c")
        cls.section_194j = cls.env.ref("l10n_in.tds_section_194j")

        # Accounts carry the section: that is how the localisation decides a
        # bill is in scope, and we do not change it.
        cls.account_194c = ChartTemplate.ref("p2107")
        cls.account_194c.l10n_in_tds_tcs_section_id = cls.section_194c
        cls.account_194j = ChartTemplate.ref("p2105")
        cls.account_194j.l10n_in_tds_tcs_section_id = cls.section_194j

        cls.tax_194c_1 = ChartTemplate.ref("tds_1_us_194c")
        cls.tax_194c_2 = ChartTemplate.ref("tds_2_us_194c")
        cls.tax_194c_20 = ChartTemplate.ref("tds_20_us_194c")
        cls.tax_194j_10 = ChartTemplate.ref("tds_10_us_194j")
        cls.tax_194j_20 = ChartTemplate.ref("tds_20_us_194j")

        cls.map_194c = cls.env["drkds.tds.rate.map"].create({
            "section_id": cls.section_194c.id,
            "company_id": cls.default_company.id,
            "normal_tax_id": cls.tax_194c_1.id,
            "higher_tax_id": cls.tax_194c_20.id,
        })

        cls.company_data["company"].l10n_in_withholding_account_id = ChartTemplate.ref("p11211")
        cls.company_data["company"].l10n_in_withholding_journal_id = cls.company_data["default_journal_misc"]

        cls.pan_with = cls.env["l10n_in.pan.entity"].create({"name": "AAAPL1234C"})
        cls.vendor_with_pan = cls.env["res.partner"].create({
            "name": "Kapoor Contractors",
            "country_id": cls.country_in.id,
            "l10n_in_pan_entity_id": cls.pan_with.id,
        })
        cls.vendor_no_pan = cls.env["res.partner"].create({
            "name": "No Papers Traders",
            "country_id": cls.country_in.id,
        })

    @classmethod
    def _bill(cls, partner, amount, account, date="2026-06-10", post=True):
        bill = cls.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": partner.id,
            "invoice_date": date,
            "date": date,
            "invoice_line_ids": [Command.create({
                "name": "Work done",
                "quantity": 1.0,
                "price_unit": amount,
                "account_id": account.id,
                "tax_ids": [Command.clear()],
            })],
        })
        if post:
            bill.action_post()
        return bill

    @classmethod
    def _wizard_model(cls, move):
        return cls.env["l10n_in.withhold.wizard"].with_context(
            active_model="account.move", active_ids=move.ids,
        )

    @classmethod
    def _wizard(cls, move):
        """An unsaved wizard, so that a proposal of no tax can be inspected.

        ``tax_id`` is required in the database, so a wizard that proposes
        nothing cannot be saved - which is the point: the user has to choose.
        """
        Wizard = cls._wizard_model(move)
        return Wizard.new(Wizard.default_get(
            ["reference", "related_move_id", "related_payment_id"]
        ))

    @classmethod
    def _withhold(cls, move, tax=None, date=None):
        """Post a withhold, using the proposed tax unless one is given."""
        tax = tax or cls._wizard(move).tax_id
        values = {"tax_id": tax.id}
        if date:
            values["date"] = date
        wizard = cls._wizard_model(move).create(values)
        return wizard.action_create_and_post_withhold()
