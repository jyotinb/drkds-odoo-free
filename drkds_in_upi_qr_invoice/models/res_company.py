import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

#: A Virtual Payment Address is ``name@handle``.
#:
#: The local part is issued by the payment service provider and may carry
#: digits, dots, dashes and underscores. The handle is the PSP identifier
#: (``okhdfcbank``, ``ybl``, ``paytm``, ...) and always starts with a letter.
#: NPCI caps the whole address at 255 characters.
UPI_VPA_RE = re.compile(
    r"^[a-zA-Z0-9][a-zA-Z0-9._\-]{1,100}@[a-zA-Z][a-zA-Z0-9.]{1,63}$"
)


def normalise_vpa(value):
    """Strip surrounding whitespace and lower-case a VPA.

    UPI handles are case insensitive, and banks print them in mixed case on
    statements. Storing one canonical form keeps the QR payload stable.
    """
    if not value:
        return False
    return value.strip().lower()


class ResCompany(models.Model):
    _inherit = "res.company"

    drkds_upi_vpa = fields.Char(
        string="UPI ID (VPA)",
        help="Virtual Payment Address money should be sent to, for example "
        "acme@okhdfcbank. Leave empty to print no QR code at all.",
    )
    drkds_upi_payee_name = fields.Char(
        string="UPI Payee Name",
        help="Name shown in the payer's UPI application. Falls back to the "
        "company name when empty.",
    )
    drkds_upi_include_amount = fields.Boolean(
        string="Pre-fill Amount",
        default=True,
        help="Embed the amount still due in the QR code. Switch this off to "
        "print an open QR code the customer types an amount into.",
    )
    drkds_upi_include_reference = fields.Boolean(
        string="Include Invoice Reference",
        default=True,
        help="Embed the invoice reference in the QR code, so the payment "
        "arrives with a note and a transaction reference you can match.",
    )

    @api.constrains("drkds_upi_vpa")
    def _check_drkds_upi_vpa(self):
        """Refuse a UPI ID that no payment application would accept.

        Blank is always allowed: it simply means this company prints no QR
        code. Anything else has to look like ``name@handle``.
        """
        for company in self:
            vpa = company.drkds_upi_vpa
            if not vpa:
                continue
            if not UPI_VPA_RE.match(vpa):
                raise ValidationError(_(
                    "%(vpa)s is not a valid UPI ID.\n\n"
                    "A UPI ID looks like acme@okhdfcbank: an identifier of "
                    "letters, digits, dots, dashes or underscores, then a "
                    "single @, then the bank handle which starts with a "
                    "letter. Spaces are not allowed.",
                    vpa=vpa,
                ))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "drkds_upi_vpa" in vals:
                vals["drkds_upi_vpa"] = normalise_vpa(vals["drkds_upi_vpa"])
        return super().create(vals_list)

    def write(self, vals):
        if "drkds_upi_vpa" in vals:
            vals = dict(vals, drkds_upi_vpa=normalise_vpa(vals["drkds_upi_vpa"]))
        return super().write(vals)
