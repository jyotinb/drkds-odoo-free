from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    recurring_id = fields.Many2one(
        "drkds.recurring.invoice", string="Recurring Template",
        readonly=True, copy=False, ondelete="set null", index="btree_not_null",
        help="Template this invoice was issued from by the recurring invoice scheduler.",
    )
