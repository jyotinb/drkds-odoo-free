import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

#: Character set used by the GSTIN check digit algorithm, in value order.
GSTIN_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z][Z][0-9A-Z]$")
IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
PIN_RE = re.compile(r"^[1-9][0-9]{5}$")

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

    drkds_in_gstin = fields.Char(
        string="GSTIN", size=15, index=True, copy=False,
        help="Fifteen character Goods and Services Tax Identification Number. "
        "Validated for structure, check digit and state on save.",
    )
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
        help="State read from the first two digits of the GSTIN.",
    )
    drkds_in_gstin_warning = fields.Char(
        string="Identifier Notice", compute="_compute_gstin_warning",
        help="Non-blocking notice, for example another contact carrying the same GSTIN.",
    )

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
        for field in ("drkds_in_gstin", "drkds_in_pan", "drkds_in_ifsc"):
            if vals.get(field):
                vals[field] = normalise(vals[field])
        if vals.get("zip"):
            vals["zip"] = vals["zip"].strip()
        return vals

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends("drkds_in_gstin")
    def _compute_state_code_id(self):
        code_model = self.env["drkds.in.state.code"].sudo()
        for partner in self:
            code = (partner.drkds_in_gstin or "")[:2]
            partner.drkds_in_state_code_id = (
                code_model.search([("code", "=", code)], limit=1) if len(code) == 2 else False
            )

    @api.depends("drkds_in_gstin", "drkds_in_pan")
    def _compute_gstin_warning(self):
        for partner in self:
            partner.drkds_in_gstin_warning = partner._duplicate_identifier_notice()

    def _duplicate_identifier_notice(self):
        """Return a sentence naming contacts that share this GSTIN, or False.

        A shared PAN is normal across branches of one business, so only a shared
        GSTIN is reported, and only as a notice.
        """
        self.ensure_one()
        if not self.drkds_in_gstin:
            return False
        domain = [("drkds_in_gstin", "=", self.drkds_in_gstin)]
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

    @api.constrains("drkds_in_gstin")
    def _check_in_gstin(self):
        for partner in self:
            gstin = partner.drkds_in_gstin
            if not gstin:
                continue
            if not GSTIN_RE.match(gstin):
                raise ValidationError(
                    _(
                        "%(gstin)s is not a valid GSTIN. A GSTIN is a two digit state "
                        "code, a PAN, an entity digit, the letter Z and a check "
                        "character, for example 27ABCDE1234F1Z5.",
                        gstin=gstin,
                    )
                )
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

    @api.constrains("drkds_in_gstin", "drkds_in_pan")
    def _check_in_gstin_pan_agree(self):
        for partner in self:
            if not (partner.drkds_in_gstin and partner.drkds_in_pan):
                continue
            embedded = partner.drkds_in_gstin[2:12]
            if embedded != partner.drkds_in_pan:
                raise ValidationError(
                    _(
                        "The PAN inside the GSTIN is %(embedded)s but the PAN field says "
                        "%(pan)s. One of the two is wrong.",
                        embedded=embedded, pan=partner.drkds_in_pan,
                    )
                )

    @api.constrains("drkds_in_gstin", "state_id")
    def _check_in_gstin_state(self):
        code_model = self.env["drkds.in.state.code"].sudo()
        for partner in self:
            if not (partner.drkds_in_gstin and partner.state_id):
                continue
            if partner.state_id.country_id.code != "IN":
                continue
            expected = code_model._code_for_state(partner.state_id)
            if not expected:
                continue
            if partner.drkds_in_gstin[:2] != expected:
                raise ValidationError(
                    _(
                        "The GSTIN starts with %(found)s but the address is in "
                        "%(state)s, whose GST state code is %(expected)s.",
                        found=partner.drkds_in_gstin[:2],
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
