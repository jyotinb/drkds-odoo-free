import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

#: Udyam registration number, the identifier issued on the Udyam Registration
#: portal since 1 July 2020. The published format is ``UDYAM-XX-00-0000000``:
#: the literal prefix ``UDYAM``, a two letter state code, a two digit district
#: code and a seven digit serial, separated by hyphens. Example from the
#: portal documentation: ``UDYAM-DL-02-0012345``.
#: Source for the format:
#: https://www.msme.llc/blog/udyam-registration-number
UDYAM_RE = re.compile(r"^UDYAM-[A-Z]{2}-[0-9]{2}-[0-9]{7}$")

#: The same value with the separators stripped, used to re-insert hyphens when
#: a user pastes the number without them.
UDYAM_COMPACT_RE = re.compile(r"^UDYAM([A-Z]{2})([0-9]{2})([0-9]{7})$")

#: Two letter state and union territory codes that may appear in a Udyam
#: number. Kept deliberately permissive: both the historic and the current
#: code are accepted where a territory was renamed or merged.
UDYAM_STATE_CODES = frozenset("""
AN AP AR AS BR CG CH CT DD DH DL DN GA GJ HP HR JH JK KA KL LA LD MH ML MN MP
MZ NL OD OR PB PY RJ SK TG TN TR TS UK UP UT WB
""".split())

#: Categories for which section 43B(h) of the Income Tax Act bites. Medium
#: enterprises are registered under the MSMED Act and appear on Udyam, but
#: section 15 of that Act - and therefore 43B(h) - covers only micro and small
#: suppliers. Treating a medium vendor as covered is the single most common
#: implementation error. Source:
#: https://taxguru.in/income-tax/section-43b-h-limitation-period-section-15-msmed-act.html
COVERED_CATEGORIES = ("micro", "small")


def normalise_udyam(value):
    """Upper-case a Udyam number, drop spaces, and restore missing hyphens."""
    if not value:
        return value
    cleaned = re.sub(r"\s+", "", value).upper()
    compact = cleaned.replace("-", "")
    match = UDYAM_COMPACT_RE.match(compact)
    if match:
        return "UDYAM-%s-%s-%s" % match.groups()
    return cleaned


class ResPartner(models.Model):
    """MSME registration details on a contact.

    Only a registered micro or small supplier starts the statutory payment
    clock, so the flag, the category and the agreement basis all live here and
    every bill reads them from the vendor.
    """

    _inherit = "res.partner"

    drkds_msme_registered = fields.Boolean(
        string="MSME Registered", copy=False,
        help="Tick when the vendor has supplied a valid Udyam registration. "
        "Only registered micro and small vendors are tracked against the "
        "statutory payment clock.",
    )
    drkds_udyam_number = fields.Char(
        string="Udyam Number", size=19, index=True, copy=False,
        help="Udyam registration number in the format UDYAM-XX-00-0000000, "
        "for example UDYAM-DL-02-0012345.",
    )
    drkds_msme_category = fields.Selection(
        selection=[
            ("micro", "Micro"),
            ("small", "Small"),
            ("medium", "Medium"),
        ],
        string="Enterprise Category", copy=False,
        help="Category shown on the Udyam certificate. The 45 day payment "
        "clock applies to micro and small only, never to medium.",
    )
    drkds_msme_registration_date = fields.Date(
        string="MSME Registration Date", copy=False,
        help="Date of Udyam registration as printed on the certificate.",
    )
    drkds_msme_has_agreement = fields.Boolean(
        string="Written Payment Agreement", default=True, copy=False,
        help="Tick when a written agreement fixes the credit period. With an "
        "agreement the limit is the agreed period, capped at 45 days. Without "
        "one the limit is 15 days.",
    )
    drkds_msme_payment_days_override = fields.Integer(
        string="Agreed Days", copy=False,
        help="Credit period agreed in writing with this vendor, in days. Leave "
        "at zero to use the company default. Cannot exceed the company's "
        "statutory maximum.",
    )
    drkds_msme_covered = fields.Boolean(
        string="MSME Clock Applies", compute="_compute_drkds_msme_covered",
        store=True, readonly=True,
        help="True for a registered micro or small vendor, which is exactly the "
        "population section 43B(h) is concerned with.",
    )
    drkds_msme_payment_days = fields.Integer(
        string="MSME Payment Days", compute="_compute_drkds_msme_payment_days",
        help="Number of days the vendor's bills may remain unpaid before the "
        "statutory limit is breached.",
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends("drkds_msme_registered", "drkds_msme_category")
    def _compute_drkds_msme_covered(self):
        for partner in self:
            partner.drkds_msme_covered = bool(
                partner.drkds_msme_registered
                and partner.drkds_msme_category in COVERED_CATEGORIES
            )

    @api.depends(
        "drkds_msme_has_agreement",
        "drkds_msme_payment_days_override",
        "company_id.drkds_msme_agreement_days",
        "company_id.drkds_msme_no_agreement_days",
    )
    def _compute_drkds_msme_payment_days(self):
        for partner in self:
            partner.drkds_msme_payment_days = partner._drkds_msme_payment_days(
                partner.company_id or self.env.company
            )

    def _drkds_msme_payment_days(self, company):
        """Return the credit period in days that applies to this vendor.

        With a written agreement the agreed period governs, defaulting to the
        company setting and capped by it. Without an agreement the buyer must
        pay before the appointed day, fifteen days from acceptance.
        """
        self.ensure_one()
        company = company or self.env.company
        if not self.drkds_msme_has_agreement:
            return company.drkds_msme_no_agreement_days
        if self.drkds_msme_payment_days_override > 0:
            return min(
                self.drkds_msme_payment_days_override,
                company.drkds_msme_agreement_days,
            )
        return company.drkds_msme_agreement_days

    # ------------------------------------------------------------------
    # Normalisation and validation
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("drkds_udyam_number"):
                vals["drkds_udyam_number"] = normalise_udyam(vals["drkds_udyam_number"])
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("drkds_udyam_number"):
            vals["drkds_udyam_number"] = normalise_udyam(vals["drkds_udyam_number"])
        return super().write(vals)

    @api.constrains("drkds_udyam_number")
    def _check_drkds_udyam_number(self):
        for partner in self:
            number = partner.drkds_udyam_number
            if not number:
                continue
            if not UDYAM_RE.match(number):
                raise ValidationError(_(
                    "%s is not a valid Udyam registration number. The format is "
                    "UDYAM-XX-00-0000000, for example UDYAM-DL-02-0012345.",
                    number,
                ))
            if number[6:8] not in UDYAM_STATE_CODES:
                raise ValidationError(_(
                    "%s does not carry a known Indian state or union territory "
                    "code in positions seven and eight.",
                    number,
                ))

    @api.constrains("drkds_msme_payment_days_override", "drkds_msme_has_agreement")
    def _check_drkds_msme_payment_days_override(self):
        for partner in self:
            company = partner.company_id or self.env.company
            days = partner.drkds_msme_payment_days_override
            if days < 0:
                raise ValidationError(_("The agreed credit period cannot be negative."))
            if days > company.drkds_msme_agreement_days:
                raise ValidationError(_(
                    "The agreed credit period for %(partner)s cannot exceed "
                    "%(days)s days.",
                    partner=partner.display_name,
                    days=company.drkds_msme_agreement_days,
                ))

    @api.constrains("drkds_msme_registered", "drkds_msme_category")
    def _check_drkds_msme_category(self):
        for partner in self:
            if partner.drkds_msme_registered and not partner.drkds_msme_category:
                raise ValidationError(_(
                    "Set the enterprise category for %s. The payment clock "
                    "applies to micro and small enterprises only, so the "
                    "category decides whether the vendor is tracked.",
                    partner.display_name,
                ))
