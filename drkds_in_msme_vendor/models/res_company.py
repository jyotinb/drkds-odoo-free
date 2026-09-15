from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

#: Statutory ceiling on an agreed credit period, in days.
#:
#: Section 15 of the Micro, Small and Medium Enterprises Development Act, 2006
#: allows the buyer and a micro or small supplier to agree a credit period in
#: writing, but "in no case" may that period exceed forty five days from the
#: day of acceptance or the day of deemed acceptance.
STATUTORY_MAX_AGREEMENT_DAYS = 45

#: Statutory limit when there is no written agreement, in days.
#:
#: With no agreement the buyer must pay before the "appointed day", defined in
#: section 2(b) of the same Act as the day following immediately after the
#: expiry of fifteen days from the day of acceptance.
STATUTORY_NO_AGREEMENT_DAYS = 15


class ResCompany(models.Model):
    """Company level MSME payment clock settings.

    The day counts are settings rather than constants for two reasons. Odoo
    databases are frequently multi-company, and a company may choose to track
    against an internal policy that is stricter than the statute. Nothing here
    may be set *longer* than the statutory ceiling, which is enforced below.

    Source for the day counts: section 15 read with section 2(b) of the Micro,
    Small and Medium Enterprises Development Act, 2006, which is the limitation
    period referred to by section 43B(h) of the Income Tax Act, 1961 (inserted
    by the Finance Act, 2023 and effective from assessment year 2024-25).
    https://taxguru.in/income-tax/section-43b-h-limitation-period-section-15-msmed-act.html
    """

    _inherit = "res.company"

    drkds_msme_agreement_days = fields.Integer(
        string="MSME Days (With Agreement)",
        default=STATUTORY_MAX_AGREEMENT_DAYS,
        help="Credit period allowed for a micro or small supplier when a written "
        "payment agreement exists. The statute caps this at 45 days; a shorter "
        "internal policy is allowed, a longer one is not.",
    )
    drkds_msme_no_agreement_days = fields.Integer(
        string="MSME Days (No Agreement)",
        default=STATUTORY_NO_AGREEMENT_DAYS,
        help="Credit period allowed for a micro or small supplier when there is no "
        "written payment agreement. The statute sets this at 15 days.",
    )
    drkds_msme_due_soon_days = fields.Integer(
        string="MSME Due Soon Window",
        default=7,
        help="Number of days before the MSME due date at which a bill starts to "
        "report as Due Soon rather than Within Limit. Presentation only.",
    )

    @api.constrains(
        "drkds_msme_agreement_days",
        "drkds_msme_no_agreement_days",
        "drkds_msme_due_soon_days",
    )
    def _check_drkds_msme_days(self):
        for company in self:
            if not 1 <= company.drkds_msme_agreement_days <= STATUTORY_MAX_AGREEMENT_DAYS:
                raise ValidationError(_(
                    "The MSME credit period with a written agreement must be between "
                    "1 and %s days. Section 15 of the MSMED Act does not allow a "
                    "longer period to be agreed.",
                    STATUTORY_MAX_AGREEMENT_DAYS,
                ))
            if not 1 <= company.drkds_msme_no_agreement_days <= STATUTORY_NO_AGREEMENT_DAYS:
                raise ValidationError(_(
                    "The MSME credit period without a written agreement must be "
                    "between 1 and %s days.",
                    STATUTORY_NO_AGREEMENT_DAYS,
                ))
            if company.drkds_msme_due_soon_days < 0:
                raise ValidationError(_("The MSME due soon window cannot be negative."))

    def write(self, vals):
        """Recompute stored MSME due dates when a day count changes."""
        result = super().write(vals)
        watched = {"drkds_msme_agreement_days", "drkds_msme_no_agreement_days"}
        if watched & set(vals):
            moves = self.env["account.move"].sudo().search([
                ("company_id", "in", self.ids),
                ("move_type", "=", "in_invoice"),
            ])
            if moves:
                moves._compute_drkds_msme_due_date()
        return result
