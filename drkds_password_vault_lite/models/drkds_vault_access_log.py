from odoo import api, fields, models


class DrkdsVaultAccessLog(models.Model):
    """One line per event that touched a secret.

    The log records *that* a secret was created, changed or revealed. It never
    records the secret, and it is append-only for ordinary users: the access
    control file grants read and create, never write or unlink.
    """

    _name = "drkds.vault.access.log"
    _description = "Vault Access Log"
    _order = "create_date desc, id desc"
    _rec_name = "entry_id"

    entry_id = fields.Many2one(
        "drkds.vault.entry", string="Entry", required=True,
        ondelete="cascade", index=True,
    )
    user_id = fields.Many2one(
        "res.users", string="User", required=True, index=True,
        default=lambda self: self.env.user,
    )
    event = fields.Selection(
        [
            ("create", "Secret stored"),
            ("update", "Secret changed"),
            ("reveal", "Secret revealed"),
        ],
        required=True, index=True,
    )
    note = fields.Char(help="Short context, never the secret itself.")

    @api.model
    def _log(self, entry, event, note=False):
        """Write an access line, bypassing record rules deliberately.

        ``sudo`` is used so the log is written even when the reveal happens in
        a restricted context; the ``user_id`` recorded is still the real user.
        """
        return self.sudo().create([{
            "entry_id": entry.id,
            "user_id": entry.env.uid,
            "event": event,
            "note": note or False,
        }])
