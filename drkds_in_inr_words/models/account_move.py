from odoo import api, fields, models


class AccountMove(models.Model):
    """Add the one amount-in-words a GST invoice needs that core has no field for.

    The invoice *total* in words already exists as ``amount_total_words``, and
    this module's currency override is what makes that field read in lakh and
    crore. No second total field is added here.

    What core has no equivalent of is the **tax** amount in words. Indian
    invoices customarily carry it, because the tax figure is the one a GST
    officer and a customer's accounts department both check by hand, and a
    figure written twice - once in digits, once in words - cannot be altered
    after the fact.
    """

    _inherit = "account.move"

    drkds_tax_amount_in_words = fields.Char(
        string="Tax Amount in Words",
        compute="_compute_drkds_tax_amount_in_words",
        help="The total tax on this document spelled out, read in lakh and "
        "crore for rupee invoices. Never stored: it always reflects the "
        "current tax total and the current wording settings.",
    )

    @api.depends("amount_tax", "currency_id", "company_id")
    @api.depends_context("lang")
    def _compute_drkds_tax_amount_in_words(self):
        """Spell the tax total through the currency, so INR reads Indian.

        ``amount_to_text`` is deliberately the entry point rather than this
        module's own helper: a non-rupee invoice then keeps Odoo's wording
        for its tax line exactly as it keeps it for its total.
        """
        for move in self:
            move.drkds_tax_amount_in_words = move.currency_id.amount_to_text(
                move.amount_tax
            ) if move.currency_id else ""
