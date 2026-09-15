from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DrkdsTdsRateMap(models.Model):
    """Which TDS tax to use for a section, per company, per PAN situation.

    Odoo's Indian localisation already ships the sections and the rates: a
    section is an ``l10n_in.section.alert`` record and every rate is an
    ``account.tax`` tagged with that section, twenty per cent variants
    included. What it does not say anywhere is *which* of those taxes is your
    normal rate for a section and which one to fall back on when the vendor
    has no PAN. That single decision is what this model records, once, so the
    withhold wizard can pick the rate by itself instead of asking every time.

    It deliberately stores no rate, no threshold and no section of its own.
    Everything it holds is a pointer at a record the localisation already owns.
    """

    _name = "drkds.tds.rate.map"
    _description = "TDS Section Rate Map"
    _order = "company_id, section_id"
    _check_company_auto = True

    section_id = fields.Many2one(
        "l10n_in.section.alert", string="TDS Section", required=True, ondelete="cascade",
        domain="[('tax_source_type', '=', 'tds')]",
        help="Section defined by the Indian localisation. Its thresholds, its "
        "alert and its tax report line all stay where they are.",
    )
    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company,
        help="Taxes belong to a company, so the mapping does too.",
    )
    normal_tax_id = fields.Many2one(
        "account.tax", string="Normal Rate", check_company=True,
        domain="[('l10n_in_tax_type', '=', 'tds_purchase'), ('l10n_in_section_id', '=', section_id)]",
        help="Rate used for a vendor who has quoted a PAN. A section often "
        "carries more than one, for example one per cent for an individual "
        "contractor and two per cent for a company, and only you can say which "
        "one your vendors fall under.",
    )
    higher_tax_id = fields.Many2one(
        "account.tax", string="Rate without PAN", check_company=True,
        domain="[('l10n_in_tax_type', '=', 'tds_purchase'), ('l10n_in_section_id', '=', section_id)]",
        help="Rate used under section 206AA when the vendor has no PAN entity, "
        "or when the PAN entity is marked for higher deduction. Normally the "
        "twenty per cent variant of the section.",
    )
    lower_tax_id = fields.Many2one(
        "account.tax", string="Lower Rate", check_company=True,
        domain="[('l10n_in_tax_type', '=', 'tds_purchase'), ('l10n_in_section_id', '=', section_id)]",
        help="Rate used when the vendor's PAN entity is marked for lower "
        "deduction, which normally means a certificate under section 197. "
        "Leave it empty and a lower deduction vendor is left for you to price "
        "by hand rather than guessed at.",
    )
    active = fields.Boolean(default=True)

    _section_company_uniq = models.Constraint(
        "unique(section_id, company_id)",
        "A TDS section can only be mapped once per company.",
    )

    @api.depends("section_id", "company_id")
    def _compute_display_name(self):
        for rate_map in self:
            rate_map.display_name = rate_map.section_id.display_name or _("New")

    @api.constrains("normal_tax_id", "higher_tax_id", "lower_tax_id", "section_id")
    def _check_taxes_belong_to_section(self):
        for rate_map in self:
            taxes = rate_map.normal_tax_id | rate_map.higher_tax_id | rate_map.lower_tax_id
            wrong = taxes.filtered(lambda tax: tax.l10n_in_section_id != rate_map.section_id)
            if wrong:
                raise ValidationError(_(
                    "The tax %(tax)s is not a rate of section %(section)s.",
                    tax=wrong[0].display_name,
                    section=rate_map.section_id.display_name,
                ))

    # ------------------------------------------------------------------
    # proposing the taxes
    # ------------------------------------------------------------------
    def _candidate_taxes(self):
        """Purchase TDS taxes the localisation ships for this section."""
        self.ensure_one()
        if not self.section_id or not self.company_id:
            return self.env["account.tax"]
        return self.env["account.tax"].search([
            *self.env["account.tax"]._check_company_domain(self.company_id),
            ("l10n_in_section_id", "=", self.section_id.id),
            ("l10n_in_tax_type", "=", "tds_purchase"),
        ])

    @api.onchange("section_id", "company_id")
    def _onchange_propose_taxes(self):
        """Fill in what can be worked out, leave the judgement to the user.

        The no-PAN rate is not a judgement call: section 206AA is the higher of
        twenty per cent and the section rate, so it is the steepest tax the
        localisation ships for the section. The normal rate is only proposed
        when the section has exactly one other rate; where a section carries
        several, choosing between them is a fact about your vendors, not about
        the Act, and the field is left empty on purpose.
        """
        for rate_map in self:
            candidates = rate_map._candidate_taxes()
            if not candidates:
                continue
            steepest = max(candidates, key=lambda tax: abs(tax.amount))
            if not rate_map.higher_tax_id:
                rate_map.higher_tax_id = steepest
            others = candidates - steepest
            if not rate_map.normal_tax_id and len(others) == 1:
                rate_map.normal_tax_id = others

    def _tax_for_deduction(self, deduction):
        """Return the tax to use for a ``tds_deduction`` setting, or an empty set.

        ``no`` returns nothing, because a vendor marked for no deduction should
        not have a rate chosen for them. ``lower`` returns nothing when no lower
        rate has been set up, rather than quietly falling back to the normal
        rate and deducting more than the vendor's certificate allows.
        """
        self.ensure_one()
        if deduction == "no":
            return self.env["account.tax"]
        if deduction == "lower":
            return self.lower_tax_id
        if deduction == "higher":
            return self.higher_tax_id or self.normal_tax_id
        return self.normal_tax_id
