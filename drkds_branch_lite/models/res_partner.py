from odoo import fields, models


class ResPartner(models.Model):
    """Branch on a contact.

    The branch on a contact says which branch owns the relationship - who walks
    in to which counter - so a branch can read its own customer list. It is a
    label only: contacts are not hidden from other branches, because contacts
    are shared master data referenced by users, companies and vendors alike.
    """

    _inherit = "res.partner"

    drkds_branch_id = fields.Many2one(
        "drkds.branch", string="Branch",
        default=lambda self: self.env.user._drkds_default_branch(),
        index="btree_not_null",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Branch this contact belongs to. Used for filtering and reporting; "
        "it does not restrict who may read the contact.",
    )
