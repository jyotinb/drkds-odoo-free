from odoo import fields, models


class AccountMove(models.Model):
    """Branch on an invoice, plus optional branch-wise numbering.

    Numbering is done through Odoo's own ``sequence.mixin`` rather than an
    ``ir.sequence``. The mixin derives the next number from the last posted
    move that matches ``_get_last_sequence_domain``; narrowing that domain to
    the branch is all it takes to give each branch an independent series, and
    it leaves gap detection, the sequence override wizard and the journal's
    own reset rules working exactly as before.
    """

    _inherit = "account.move"

    drkds_branch_id = fields.Many2one(
        "drkds.lite.branch", string="Branch",
        default=lambda self: self.env.user._drkds_default_branch(),
        index="btree_not_null",
        domain="[('company_id', '=', company_id)]",
        check_company=False,
        tracking=True,
        help="Branch this document belongs to. Set before posting: once the "
        "number is drawn from a branch series, moving the document would break "
        "that series.",
    )

    def _drkds_use_branch_sequence(self):
        """True when this move should draw from a branch-specific series."""
        self.ensure_one()
        return bool(
            self.company_id.drkds_branch_invoice_sequence
            and self.is_sale_document(include_receipts=True)
        )

    def _get_last_sequence_domain(self, relaxed=False):
        # EXTENDS account.move - keep each branch's series independent.
        where_string, param = super()._get_last_sequence_domain(relaxed)
        if self._drkds_use_branch_sequence():
            if self.drkds_branch_id:
                where_string += " AND drkds_branch_id = %(drkds_branch_id)s "
                param["drkds_branch_id"] = self.drkds_branch_id.id
            else:
                where_string += " AND drkds_branch_id IS NULL "
        return where_string, param

    def _get_starting_sequence(self):
        # EXTENDS account.move - put the branch code next to the journal code.
        starting_sequence = super()._get_starting_sequence()
        if self._drkds_use_branch_sequence() and self.drkds_branch_id:
            prefix, separator, rest = starting_sequence.partition("/")
            code = self.drkds_branch_id.code
            starting_sequence = f"{prefix}-{code}{separator}{rest}"
        return starting_sequence
