from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    drkds_branch_invoice_sequence = fields.Boolean(
        string="Branch-wise Invoice Numbering",
        help="Give every branch its own invoice number series inside the same "
        "journal, by inserting the branch code into the number. Switch this on "
        "before the first invoice of a period; changing it mid-series leaves a "
        "gap that an auditor will ask about.",
    )
