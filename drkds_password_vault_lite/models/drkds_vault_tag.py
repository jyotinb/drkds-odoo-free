from odoo import fields, models


class DrkdsVaultTag(models.Model):
    """A personal label for vault entries, for example 'work' or 'banking'."""

    _name = "drkds.vault.tag"
    _description = "Vault Tag"
    _order = "name"

    name = fields.Char(required=True)
    color = fields.Integer(string="Colour")
    user_id = fields.Many2one(
        "res.users", string="Owner", required=True, index=True, ondelete="cascade",
        default=lambda self: self.env.user,
    )

    _name_user_uniq = models.Constraint(
        "unique(name, user_id)",
        "You already have a vault tag with this name.",
    )
