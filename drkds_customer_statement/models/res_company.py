from odoo import fields, models


class ResCompany(models.Model):
    """Company settings printed on every statement of account."""

    _inherit = "res.company"

    drkds_statement_bank_id = fields.Many2one(
        "res.partner.bank", string="Statement Bank Account",
        domain="[('partner_id', '=', partner_id)]",
        ondelete="set null",
        help="Company bank account printed on the statement so the customer "
        "knows where to pay. Leave empty to print none.",
    )
    drkds_statement_note = fields.Text(
        string="Statement Footer Note",
        help="Free text printed at the foot of every statement, for example "
        "payment instructions or a dispute contact.",
    )
