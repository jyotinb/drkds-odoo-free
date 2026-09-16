from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class DrkdsVaultEntry(models.Model):
    """One credential in one person's vault.

    The password lives in ``secret_encrypted`` as a Fernet token and nowhere
    else. ``secret`` is a write-only, non-stored field: it is how a new value
    is typed in, it always reads back empty, it cannot be searched on and it
    cannot be exported. Reading a secret back is a deliberate act through the
    reveal wizard, and it leaves a line in the access log.
    """

    _name = "drkds.lite.vault.entry"
    _description = "Vault Entry"
    _order = "name"

    name = fields.Char(string="Title", required=True, index=True)
    url = fields.Char(string="URL", help="Where these credentials are used.")
    username = fields.Char(string="Username")
    notes = fields.Text(
        help="Free text. Stored in clear: keep passwords out of it, they "
             "belong in the Password field.",
    )
    folder_id = fields.Many2one(
        "drkds.vault.folder", string="Folder", ondelete="set null",
        domain="[('user_id', '=', user_id)]",
    )
    tag_ids = fields.Many2many(
        "drkds.lite.vault.tag", string="Tags", domain="[('user_id', '=', user_id)]",
    )
    user_id = fields.Many2one(
        "res.users", string="Owner", required=True, index=True, ondelete="cascade",
        default=lambda self: self.env.user,
        help="The only user who can see this entry. Ownership cannot be "
             "changed once the entry exists.",
    )
    active = fields.Boolean(default=True)

    secret_encrypted = fields.Char(
        string="Encrypted Secret", copy=False, exportable=False,
        help="Fernet token. Meaningless without the server's vault key.",
    )
    secret = fields.Char(
        string="Password", store=False, copy=False, exportable=False,
        compute="_compute_secret", inverse="_inverse_secret",
        help="Type a new password here to replace the stored one. It is "
             "encrypted on save and never shown again by this field.",
    )
    has_secret = fields.Boolean(
        string="Has a password", compute="_compute_has_secret", store=True,
        help="Whether a password is currently stored, without revealing it.",
    )
    access_log_ids = fields.One2many(
        "drkds.lite.vault.access.log", "entry_id", string="Access Log", readonly=True,
    )
    last_access_date = fields.Datetime(
        string="Last Revealed", compute="_compute_last_access", store=False,
    )

    # ------------------------------------------------------------------
    # computes
    # ------------------------------------------------------------------
    def _compute_secret(self):
        """Always empty. The stored password is never pushed to a client."""
        for entry in self:
            entry.secret = False

    def _inverse_secret(self):
        """Encrypt whatever was typed, then forget the plaintext."""
        crypto = self.env["drkds.vault.crypto"]
        for entry in self:
            typed = entry.secret
            if typed is False or typed is None:
                # Untouched field on an ordinary save: leave the stored token be.
                continue
            if typed == "":
                entry.secret_encrypted = False
                continue
            entry.secret_encrypted = crypto._encrypt(typed)

    @api.depends("secret_encrypted")
    def _compute_has_secret(self):
        for entry in self:
            entry.has_secret = bool(entry.secret_encrypted)

    def _compute_last_access(self):
        log = self.env["drkds.lite.vault.access.log"]
        for entry in self:
            last = log.search(
                [("entry_id", "=", entry.id), ("event", "=", "reveal")],
                order="create_date desc", limit=1,
            )
            entry.last_access_date = last.create_date or False

    # ------------------------------------------------------------------
    # ownership and logging
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Ownership is not a client decision: an entry always belongs to
            # whoever creates it, so it can never be planted in someone else's
            # vault.
            vals["user_id"] = self.env.uid
            if "secret" in vals and vals["secret"]:
                # Fail before the row exists rather than after.
                self.env["drkds.vault.crypto"]._self_check()
        entries = super().create(vals_list)
        for entry in entries:
            if entry.secret_encrypted:
                self.env["drkds.lite.vault.access.log"]._log(entry, "create")
        return entries

    def write(self, vals):
        if "user_id" in vals and any(
            entry.user_id.id != vals["user_id"] for entry in self
        ):
            raise UserError(_(
                "A vault entry cannot be handed to another user. Sharing is "
                "not part of this module."
            ))
        changing_secret = bool(vals.get("secret"))
        result = super().write(vals)
        if changing_secret:
            for entry in self:
                self.env["drkds.lite.vault.access.log"]._log(entry, "update")
        return result

    def copy_data(self, default=None):
        """Duplicating an entry never carries the password across."""
        vals_list = super().copy_data(default=default)
        for vals in vals_list:
            vals.pop("secret_encrypted", None)
        return vals_list

    # ------------------------------------------------------------------
    # reveal
    # ------------------------------------------------------------------
    def _read_secret(self):
        """Decrypt and return the secret, logging the access. Owner only."""
        self.ensure_one()
        if self.user_id.id != self.env.uid and not self.env.su:
            raise AccessError(_("This vault entry does not belong to you."))
        if not self.secret_encrypted:
            raise UserError(_("This entry has no password stored."))
        plaintext = self.env["drkds.vault.crypto"]._decrypt(self.secret_encrypted)
        self.env["drkds.lite.vault.access.log"]._log(self, "reveal")
        return plaintext

    def action_reveal_secret(self):
        """Open the reveal wizard for this entry."""
        self.ensure_one()
        wizard = self.env["drkds.vault.reveal"].create([{"entry_id": self.id}])
        return {
            "type": "ir.actions.act_window",
            "name": _("Reveal Password"),
            "res_model": "drkds.vault.reveal",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_open_access_log(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Access Log"),
            "res_model": "drkds.lite.vault.access.log",
            "view_mode": "list",
            "domain": [("entry_id", "=", self.id)],
        }
