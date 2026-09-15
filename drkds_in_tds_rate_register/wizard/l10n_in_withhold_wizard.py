from odoo import _, api, fields, models


class L10nInWithholdWizard(models.TransientModel):
    """Choose the TDS rate for the user instead of asking them to remember it.

    The localisation's wizard already computes the base, the amount and the
    entry. Its one weak spot is the rate: it guesses from the last withhold
    posted for the same PAN, account and section, and where the vendor has no
    PAN it does no more than print a sentence asking the user to remember the
    higher rate. This extension turns that sentence into the selected tax.

    It extends rather than replaces. The localisation's guess runs first and
    is left alone whenever the vendor's situation is unremarkable; the rate map
    only speaks up where it knows something the guess cannot, and the field
    stays editable so the user always has the last word.
    """

    _inherit = "l10n_in.withhold.wizard"

    drkds_rate_reason = fields.Char(
        string="Rate Chosen Because",
        compute="_compute_drkds_rate_reason",
        help="Why this rate was proposed. Change the tax if you disagree.",
    )
    drkds_rate_map_id = fields.Many2one(
        "drkds.tds.rate.map", string="Rate Map",
        compute="_compute_drkds_rate_map_id",
        help="The section rate map the proposal came from.",
    )

    # ------------------------------------------------------------------
    # section and rate map
    # ------------------------------------------------------------------
    def _drkds_sections(self):
        """TDS sections in play on the related bill, best candidate first.

        The sections whose thresholds the localisation says are crossed come
        first, because that is the reason the user opened this wizard. Behind
        them come the sections carried by the bill's accounts, so that a
        deliberate deduction below a threshold, or a second deduction on a bill
        that already has one, still gets a rate proposed.
        """
        self.ensure_one()
        move = self.related_move_id
        if not move:
            return self.env["l10n_in.section.alert"]
        tagged = move.line_ids.account_id.l10n_in_tds_tcs_section_id.filtered(
            lambda section: section.tax_source_type == "tds"
        )
        alerting = move._get_l10n_in_tds_tcs_applicable_sections() & tagged
        return alerting + (tagged - alerting)

    @api.depends("related_move_id", "related_payment_id")
    def _compute_drkds_rate_map_id(self):
        for wizard in self:
            rate_map = self.env["drkds.tds.rate.map"]
            if wizard.l10n_in_tds_tax_type == "tds_purchase":
                for section in wizard._drkds_sections():
                    rate_map = section._drkds_rate_map(wizard.company_id)
                    if rate_map:
                        break
            wizard.drkds_rate_map_id = rate_map

    def _drkds_proposed_tax(self):
        """Return the tax the rate map proposes for this wizard, or an empty set."""
        self.ensure_one()
        if self.l10n_in_tds_tax_type != "tds_purchase" or not self.drkds_rate_map_id:
            return self.env["account.tax"]
        return self.drkds_rate_map_id._tax_for_deduction(self.tds_deduction or "normal")

    # ------------------------------------------------------------------
    # the rate itself
    # ------------------------------------------------------------------
    def _compute_tax_id(self):
        super()._compute_tax_id()
        for wizard in self:
            proposal = wizard._drkds_proposed_tax()
            if not proposal:
                continue
            if wizard.tds_deduction == "normal" and wizard.tax_id:
                # Nothing unusual about this vendor, and the localisation
                # already recognised the section from an earlier withhold.
                # Its answer is at least as well informed as ours.
                continue
            wizard.tax_id = proposal

    @api.depends("tax_id", "tds_deduction", "drkds_rate_map_id")
    def _compute_drkds_rate_reason(self):
        for wizard in self:
            reason = False
            proposal = wizard._drkds_proposed_tax()
            if proposal and proposal == wizard.tax_id:
                section = wizard.drkds_rate_map_id.section_id.name
                match wizard.tds_deduction:
                    case "higher":
                        reason = _(
                            "Vendor has no PAN entity, or is marked for higher "
                            "deduction, so the section %s rate without PAN was used.",
                            section,
                        )
                    case "lower":
                        reason = _(
                            "Vendor is marked for lower deduction, so the lower "
                            "rate set up for section %s was used.", section,
                        )
                    case "no":
                        reason = False
                    case _:
                        reason = _(
                            "Vendor has a PAN, so the normal rate for section %s "
                            "was used.", section,
                        )
            elif wizard.tds_deduction == "lower" and wizard.drkds_rate_map_id \
                    and not wizard.drkds_rate_map_id.lower_tax_id:
                reason = _(
                    "Vendor is marked for lower deduction but section %s has no "
                    "lower rate set up, so no rate was proposed. Choose one yourself.",
                    wizard.drkds_rate_map_id.section_id.name,
                )
            wizard.drkds_rate_reason = reason
