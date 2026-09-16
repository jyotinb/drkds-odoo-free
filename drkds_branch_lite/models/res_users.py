from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    """Where a user's branch comes from.

    Counter staff should never have to pick a branch. They get one default
    branch, it lands on every document they create, and the record rules keep
    them inside the branches they are allowed to see.
    """

    _inherit = "res.users"

    drkds_branch_id = fields.Many2one(
        "drkds.lite.branch", string="Default Branch",
        domain="[('company_id', 'in', company_ids)]",
        help="Branch put on sales orders, invoices and contacts this user creates. "
        "The user can still change it on the document if their allowed branches "
        "include more than one.",
    )
    drkds_branch_ids = fields.Many2many(
        "drkds.lite.branch", "drkds_lite_branch_res_users_rel", "user_id", "branch_id",
        string="Allowed Branches",
        help="Branches this user may see and use. Leave empty to give the user "
        "an unrestricted view of every branch, which is what an owner or an "
        "accountant normally needs.",
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["drkds_branch_id", "drkds_branch_ids"]

    @api.constrains("drkds_branch_id", "drkds_branch_ids")
    def _check_default_branch_allowed(self):
        for user in self:
            if user.drkds_branch_id and user.drkds_branch_ids and \
                    user.drkds_branch_id not in user.drkds_branch_ids:
                raise ValidationError(_(
                    "%(user)s has %(branch)s as default branch, which is not in "
                    "their allowed branches.",
                    user=user.name, branch=user.drkds_branch_id.display_name,
                ))

    @api.onchange("drkds_branch_id")
    def _onchange_drkds_branch_id(self):
        """Keep the default branch inside the allowed list, silently."""
        if self.drkds_branch_id and self.drkds_branch_ids and \
                self.drkds_branch_id not in self.drkds_branch_ids:
            self.drkds_branch_ids |= self.drkds_branch_id

    def _drkds_default_branch(self):
        """Return the branch a document created by this user should carry."""
        self.ensure_one()
        branch = self.drkds_branch_id
        if not branch and len(self.drkds_branch_ids) == 1:
            branch = self.drkds_branch_ids
        return branch.filtered(lambda b: b.company_id == self.env.company)
