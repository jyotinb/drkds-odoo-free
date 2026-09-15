from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DrkdsBranch(models.Model):
    """A place of business inside one company.

    A branch is deliberately not a company. It carries no chart of accounts, no
    currency and no separate books: it is a label on documents, a default for a
    user, and the key a record rule and a group-by read. Everything a branch
    touches stays inside a single ``res.company`` and, in India, a single GSTIN.
    """

    _name = "drkds.branch"
    _description = "Branch"
    _order = "sequence, code"
    _rec_name = "display_name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(
        required=True, size=8,
        help="Short branch code, used in filters and, when branch numbering is "
        "switched on, inside the invoice number. Keep it short: BLR, MUM, HO.",
    )
    sequence = fields.Integer(default=10, help="Order the branch appears in.")
    active = fields.Boolean(
        default=True,
        help="Archive a branch that has closed. Its past documents keep the "
        "branch and stay readable; the branch stops being offered on new ones.",
    )
    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company, ondelete="cascade",
        help="A branch belongs to exactly one company. Branches never span companies.",
    )

    street = fields.Char()
    street2 = fields.Char()
    city = fields.Char()
    state_id = fields.Many2one(
        "res.country.state", string="State",
        domain="[('country_id', '=?', country_id)]",
    )
    zip = fields.Char(string="ZIP")
    country_id = fields.Many2one(
        "res.country", string="Country",
        default=lambda self: self.env.company.country_id,
    )
    phone = fields.Char()
    email = fields.Char()
    manager_id = fields.Many2one(
        "res.users", string="Branch Manager",
        domain="[('share', '=', False)]",
        help="Informational. The manager is not granted any extra access by this field.",
    )
    note = fields.Text(string="Internal Notes")

    _code_company_uniq = models.Constraint(
        "unique(code, company_id)",
        "A branch code must be unique within a company.",
    )

    @api.depends("name", "code")
    def _compute_display_name(self):
        for branch in self:
            branch.display_name = f"[{branch.code}] {branch.name}" if branch.code else branch.name

    @api.constrains("code")
    def _check_code(self):
        for branch in self:
            code = (branch.code or "").strip()
            if not code:
                raise ValidationError(_("A branch needs a code."))
            if not code.replace("-", "").replace("_", "").isalnum():
                raise ValidationError(
                    _("The branch code %s may only contain letters, digits, - and _.", branch.code)
                )

    @api.onchange("code")
    def _onchange_code(self):
        if self.code:
            self.code = self.code.strip().upper()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code"):
                vals["code"] = vals["code"].strip().upper()
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("code"):
            vals["code"] = vals["code"].strip().upper()
        return super().write(vals)
