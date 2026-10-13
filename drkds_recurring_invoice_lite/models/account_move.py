from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    # Salespeople read invoices but not templates: without groups the field
    # would reach a model they cannot read from the invoice form and search.
    recurring_id = fields.Many2one(
        "drkds.recurring.invoice", string="Recurring Template",
        readonly=True, copy=False, ondelete="set null", index="btree_not_null",
        groups="account.group_account_invoice,account.group_account_readonly",
        help="Template this invoice was issued from by the recurring invoice scheduler.",
    )
