from odoo import fields, models


class ResCompany(models.Model):
    """Company level defaults for the fixed asset register."""

    _inherit = "res.company"

    drkds_asset_fy_last_month = fields.Selection(
        [
            ("1", "January"), ("2", "February"), ("3", "March"), ("4", "April"),
            ("5", "May"), ("6", "June"), ("7", "July"), ("8", "August"),
            ("9", "September"), ("10", "October"), ("11", "November"), ("12", "December"),
        ],
        string="Asset Year Ends In", default="3", required=True,
        help="Month the financial year closes in. Yearly depreciation periods are "
             "cut on this boundary, so a mid-year purchase is pro-rated.",
    )
    drkds_asset_fy_last_day = fields.Integer(
        string="Asset Year Ends On Day", default=31, required=True,
        help="Day of that month the financial year closes on. A day past the end "
             "of the month is clamped to the last day.",
    )
