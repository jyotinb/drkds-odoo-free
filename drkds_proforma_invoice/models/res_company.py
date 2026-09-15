from odoo import _, api, fields, models

DEFAULT_PROFORMA_DISCLAIMER = (
    "This document is a proforma invoice. It is not a tax invoice, it creates "
    "no accounting entry and no tax liability, and it confers no right to "
    "input tax credit or to any tax deduction. A tax invoice will be issued "
    "separately once the supply is made."
)


class ResCompany(models.Model):
    """Company level wording for the proforma disclaimer."""

    _inherit = "res.company"

    drkds_proforma_disclaimer = fields.Text(
        string="Proforma Disclaimer",
        default=lambda self: _(DEFAULT_PROFORMA_DISCLAIMER),
        help="Printed prominently on every proforma invoice PDF. Adjust it to "
        "match local practice and language.",
    )

    @api.model
    def _drkds_default_proforma_disclaimer(self):
        return _(DEFAULT_PROFORMA_DISCLAIMER)
