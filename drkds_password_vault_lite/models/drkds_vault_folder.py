from odoo import api, fields, models


class DrkdsVaultFolder(models.Model):
    """A personal folder grouping vault entries. Private to its owner."""

    _name = "drkds.vault.folder"
    _description = "Vault Folder"
    _order = "name"

    name = fields.Char(required=True)
    user_id = fields.Many2one(
        "res.users", string="Owner", required=True, index=True, ondelete="cascade",
        default=lambda self: self.env.user,
        help="Folders are personal. Only the owner sees them.",
    )
    entry_ids = fields.One2many("drkds.vault.entry", "folder_id", string="Entries")
    entry_count = fields.Integer(compute="_compute_entry_count")
    active = fields.Boolean(default=True)

    _name_user_uniq = models.Constraint(
        "unique(name, user_id)",
        "You already have a vault folder with this name.",
    )

    @api.depends("entry_ids")
    def _compute_entry_count(self):
        for folder in self:
            folder.entry_count = len(folder.entry_ids)
