"""Company settings for the e-way bill watch.

Both figures are settings rather than constants. The kilometres that buy one
day of validity moved from 100 to 200 in 2021 and is 20 for over dimensional
cargo, and the fifty thousand rupee threshold varies by state for movement
inside the state.
"""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    drkds_eway_km_per_day = fields.Integer(
        string="E-Way Bill km per Day", default=200,
        help="Kilometres of declared distance that buy one day of validity, used "
        "only to suggest an expected expiry date for comparison. Rule 138(10) of "
        "the CGST Rules says 200 km or part thereof for regular cargo; over "
        "dimensional cargo is 20 km.",
    )
    drkds_eway_threshold = fields.Float(
        string="E-Way Bill Threshold", default=50000.0,
        help="Invoice value at or above which a posted customer document with no "
        "generated e-way bill is listed as a reminder. Fifty thousand rupees is "
        "the usual figure; some states set a different limit for movement inside "
        "the state.",
    )

    @api.constrains("drkds_eway_km_per_day")
    def _check_drkds_eway_km_per_day(self):
        for company in self:
            if company.drkds_eway_km_per_day <= 0:
                raise ValidationError(_("Kilometres per day must be greater than zero."))


