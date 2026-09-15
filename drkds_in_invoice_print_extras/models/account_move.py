"""Small helpers used by the Indian invoice print extras template.

This module adds no report of its own and changes no computed amount. The
standard Indian invoice PDF, produced by Odoo's own ``l10n_in`` localisation,
stays exactly as it is; these helpers only feed the handful of extra blocks
that template does not print.

Everything here is deliberately read-only: a helper that returned a different
number from the one on the invoice would be a bug, not a feature.
"""

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    drkds_in_show_print_extras = fields.Boolean(
        string="Show Indian Print Extras",
        compute="_compute_drkds_in_show_print_extras",
        help="Technical flag used by the invoice report. True when the company "
        "is Indian and GST registered, which is the same condition the "
        "localisation itself uses to decide whether to print GST details.",
    )
    drkds_in_has_reverse_charge = fields.Boolean(
        string="Has Reverse Charge Tax",
        compute="_compute_drkds_in_has_reverse_charge",
        help="True when at least one tax on the invoice lines is flagged as "
        "reverse charge in the Indian localisation.",
    )

    @api.depends("company_id.account_fiscal_country_id", "company_id.l10n_in_is_gst_registered")
    def _compute_drkds_in_show_print_extras(self):
        """Mirror the condition l10n_in uses to gate its own GST blocks.

        Printing a GST state code on the invoice of a company that is not GST
        registered would be worse than printing nothing, so the extras follow
        the localisation rather than inventing their own rule.
        """
        for move in self:
            company = move.company_id
            move.drkds_in_show_print_extras = bool(
                company.account_fiscal_country_id.code == "IN"
                and company.l10n_in_is_gst_registered
            )

    @api.depends("invoice_line_ids.tax_ids.l10n_in_reverse_charge")
    def _compute_drkds_in_has_reverse_charge(self):
        """Flag an invoice where the buyer, not the supplier, pays the GST.

        The flag comes from ``l10n_in_reverse_charge`` on the tax itself, which
        the localisation already maintains and shows on the tax form. It is
        simply never printed on the invoice.
        """
        for move in self:
            move.drkds_in_has_reverse_charge = any(
                move.invoice_line_ids.tax_ids.mapped("l10n_in_reverse_charge")
            )

    def drkds_in_bank_account(self):
        """Return the bank account to print, or an empty recordset.

        The invoice's own recipient bank wins, because that is the account the
        customer is being asked to pay into. The company's first bank account
        is the fallback, so an invoice that was never given a recipient bank
        still prints usable payment details instead of nothing.
        """
        self.ensure_one()
        return self.partner_bank_id or self.company_id.partner_id.bank_ids[:1]
