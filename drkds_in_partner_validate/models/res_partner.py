import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

#: Character set used by the GSTIN check digit algorithm, in value order.
GSTIN_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
PIN_RE = re.compile(r"^[1-9][0-9]{5}$")

#: The ordinary GSTIN: a two digit state code, a PAN, an entity digit, the
#: letter Z and a check character. This mirrors the first of the five patterns
#: in ``base_vat.check_vat_in`` (normal, composite and casual taxpayers), on an
#: already upper-cased number. It is deliberately the *only* shape the check
#: digit is applied to; see :meth:`ResPartner.check_vat_in`.
GSTIN_NORMAL_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")

#: Any fifteen character number that could be a GSTIN of some kind. Used only
#: to decide whether a ``vat`` deserves the Indian treatment when the contact
#: carries no country yet; validity itself always comes from ``check_vat_in``.
GSTIN_SHAPE_RE = re.compile(r"^[0-9]{2}[0-9A-Z]{13}$")

#: Fourth character of a PAN, the holder type.
PAN_HOLDER_TYPES = set("ABCFGHLJPTKE")


def normalise(value):
    """Upper-case and strip spaces, dashes and dots from an identifier."""
    if not value:
        return value
    return re.sub(r"[\s\-.]", "", value).upper()


def gstin_check_digit(first_fourteen):
    """Return the check digit for the first fourteen characters of a GSTIN.

    The algorithm is the one published by GSTN: each character is converted to
    its position in a base 36 alphabet and multiplied by an alternating factor
    of one and two. The quotient and remainder of each product against 36 are
    summed, and the check digit is whatever brings that sum to a multiple of 36.
    """
    total = 0
    for index, char in enumerate(first_fourteen):
        value = GSTIN_ALPHABET.index(char)
        factor = 2 if index % 2 else 1
        product = value * factor
        total += product // 36 + product % 36
    return GSTIN_ALPHABET[(36 - total % 36) % 36]


class ResPartner(models.Model):
    _inherit = "res.partner"

    drkds_in_pan = fields.Char(
        string="PAN", size=10, index=True, copy=False,
        help="Ten character Permanent Account Number.",
    )
    drkds_in_ifsc = fields.Char(
        string="IFSC", size=11, copy=False,
        help="Eleven character Indian Financial System Code of the partner's bank branch.",
    )
    drkds_in_state_code_id = fields.Many2one(
        "drkds.in.state.code", string="GST State", compute="_compute_state_code_id",
        store=True, readonly=True,
        help="State read from the first two digits of the GSTIN held in the Tax ID field.",
    )
    drkds_in_gstin_warning = fields.Char(
        string="Identifier Notice", compute="_compute_gstin_warning",
        help="Non-blocking notice, for example another contact carrying the same GSTIN.",
    )

    # ------------------------------------------------------------------
    # GSTIN access
    # ------------------------------------------------------------------
    def _drkds_in_gstin(self):
        """Return the GSTIN held in the standard ``vat`` field, or False.

        Indian users keep the GSTIN in ``vat``; that is where ``l10n_in`` reads
        it from, so this module reads it from there too rather than carrying a
        second, competing field.

        A ``vat`` is treated as a GSTIN when the contact is in India, or when it
        has no country yet but the number already has the fifteen character
        GSTIN shape.
        """
        self.ensure_one()
        vat = normalise(self.vat)
        if not vat or len(vat) != 15:
            return False
        country_code = self.country_id.code
        if country_code and country_code != "IN":
            return False
        if not country_code and not GSTIN_SHAPE_RE.match(vat):
            return False
        return vat

    # ------------------------------------------------------------------
    # Structure check, extended with the check digit
    # ------------------------------------------------------------------
    def check_vat_in(self, vat):
        """Add the GSTIN check digit to Odoo's own structure check.

        ``base_vat.check_vat_in`` is a regular expression test only: it accepts
        five shapes (normal/composite/casual, UN or ON body, NRI, TDS and TCS)
        and never verifies the fifteenth character. This override keeps all of
        that -- ``super()`` decides the structure, and a number core refuses is
        refused here too -- and adds the published GSTN check digit on top.

        Deliberate limitation: the check digit is applied **only** to the
        ordinary GSTIN form, a two digit state code followed by a PAN. The
        UN/ON body, NRI, TDS and TCS forms are accepted on core's regex alone,
        because the same check-digit convention is not confirmed for them and
        wrongly refusing a real registration is far worse than letting a
        mistyped exotic number through.

        Method resolution order matters here: ``l10n_in`` returns True early for
        its ``TEST_GST_NUMBER`` EDI credential, and this override must not undo
        that whichever way round the two modules are loaded. That number does
        not match :data:`GSTIN_NORMAL_RE`, so it is never check-digit tested.
        """
        if not super().check_vat_in(vat):
            return False
        number = (vat or "").upper()
        if not GSTIN_NORMAL_RE.match(number):
            # An exotic but structurally valid form: trust core.
            return True
        return number[14] == gstin_check_digit(number[:14])

    # ------------------------------------------------------------------
    # Normalisation
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._normalise_in_identifiers(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._normalise_in_identifiers(vals)
        return super().write(vals)

    @api.model
    def _normalise_in_identifiers(self, vals):
        """Tidy the Indian identifiers in ``vals`` in place.

        ``vat`` is only reshaped when the cleaned-up value looks like a GSTIN,
        so a French or Brazilian tax id is left exactly as typed.
        """
        for field in ("drkds_in_pan", "drkds_in_ifsc"):
            if vals.get(field):
                vals[field] = normalise(vals[field])
        if vals.get("vat"):
            candidate = normalise(vals["vat"])
            if GSTIN_SHAPE_RE.match(candidate):
                vals["vat"] = candidate
        if vals.get("zip"):
            vals["zip"] = vals["zip"].strip()
        return vals

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends("vat", "country_id")
    def _compute_state_code_id(self):
        code_model = self.env["drkds.in.state.code"].sudo()
        for partner in self:
            gstin = partner._drkds_in_gstin()
            partner.drkds_in_state_code_id = (
                code_model.search([("code", "=", gstin[:2])], limit=1) if gstin else False
            )

    @api.depends("vat", "country_id", "drkds_in_pan")
    def _compute_gstin_warning(self):
        for partner in self:
            partner.drkds_in_gstin_warning = partner._duplicate_identifier_notice()

    def _duplicate_identifier_notice(self):
        """Return a sentence naming contacts that share this GSTIN, or False.

        A shared PAN is normal across branches of one business, so only a shared
        GSTIN is reported, and only as a notice.
        """
        self.ensure_one()
        gstin = self._drkds_in_gstin()
        if not gstin:
            return False
        domain = [("vat", "=", gstin)]
        if isinstance(self.id, int):
            domain.append(("id", "!=", self.id))
        others = self.sudo().search(domain, limit=3)
        if not others:
            return False
        return _(
            "This GSTIN is also on: %s", ", ".join(others.mapped("display_name"))
        )

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains("drkds_in_pan")
    def _check_in_pan(self):
        for partner in self:
            pan = partner.drkds_in_pan
            if not pan:
                continue
            if not PAN_RE.match(pan):
                raise ValidationError(
                    _(
                        "%(pan)s is not a valid PAN. A PAN is five letters, then four "
                        "digits, then one letter, for example ABCDE1234F.",
                        pan=pan,
                    )
                )
            if pan[3] not in PAN_HOLDER_TYPES:
                raise ValidationError(
                    _(
                        "%(pan)s is not a valid PAN. The fourth character is the holder "
                        "type and %(char)s is not one that the income tax department issues.",
                        pan=pan, char=pan[3],
                    )
                )

    @api.constrains("vat", "country_id")
    def _check_in_gstin(self):
        """Explain a failed check digit, and cover contacts with no country.

        ``base_vat`` already refuses an invalid GSTIN on an Indian contact, but
        its message only says the number is wrong. This names the character that
        was expected, which is what turns a rejection into a correction.
        """
        for partner in self:
            gstin = partner._drkds_in_gstin()
            if not gstin or not GSTIN_NORMAL_RE.match(gstin):
                continue
            expected = gstin_check_digit(gstin[:14])
            if gstin[14] != expected:
                raise ValidationError(
                    _(
                        "%(gstin)s fails its check digit. The last character should be "
                        "%(expected)s. Please re-read the number from the registration "
                        "certificate.",
                        gstin=gstin, expected=expected,
                    )
                )

    @api.constrains("vat", "country_id", "drkds_in_pan")
    def _check_in_gstin_pan_agree(self):
        for partner in self:
            gstin = partner._drkds_in_gstin()
            if not (gstin and partner.drkds_in_pan):
                continue
            if not GSTIN_NORMAL_RE.match(gstin):
                # Only the ordinary form carries a PAN in characters 3 to 12.
                continue
            embedded = gstin[2:12]
            if embedded != partner.drkds_in_pan:
                raise ValidationError(
                    _(
                        "The PAN inside the GSTIN is %(embedded)s but the PAN field says "
                        "%(pan)s. One of the two is wrong.",
                        embedded=embedded, pan=partner.drkds_in_pan,
                    )
                )

    @api.constrains("vat", "country_id", "state_id")
    def _check_in_gstin_state(self):
        code_model = self.env["drkds.in.state.code"].sudo()
        for partner in self:
            gstin = partner._drkds_in_gstin()
            if not (gstin and partner.state_id):
                continue
            if partner.state_id.country_id.code != "IN":
                continue
            expected = code_model._code_for_state(partner.state_id)
            if not expected:
                continue
            if gstin[:2] != expected:
                raise ValidationError(
                    _(
                        "The GSTIN starts with %(found)s but the address is in "
                        "%(state)s, whose GST state code is %(expected)s.",
                        found=gstin[:2],
                        state=partner.state_id.name,
                        expected=expected,
                    )
                )

    @api.constrains("drkds_in_ifsc")
    def _check_in_ifsc(self):
        for partner in self:
            ifsc = partner.drkds_in_ifsc
            if ifsc and not IFSC_RE.match(ifsc):
                raise ValidationError(
                    _(
                        "%(ifsc)s is not a valid IFSC. An IFSC is four letters, then a "
                        "zero, then six more characters, for example HDFC0001234.",
                        ifsc=ifsc,
                    )
                )

    @api.constrains("zip", "country_id")
    def _check_in_zip(self):
        for partner in self:
            if not (partner.zip and partner.country_id.code == "IN"):
                continue
            if not PIN_RE.match(partner.zip.strip()):
                raise ValidationError(
                    _(
                        "%(zip)s is not a valid Indian PIN code. A PIN code is six "
                        "digits and never starts with zero.",
                        zip=partner.zip,
                    )
                )
