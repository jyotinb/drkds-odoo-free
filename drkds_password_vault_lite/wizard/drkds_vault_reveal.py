from odoo import _, api, fields, models


class DrkdsVaultReveal(models.TransientModel):
    """The one place a stored password is shown back to its owner.

    The plaintext lives on a transient record for the length of the dialog and
    is never written to a permanent table. Opening this wizard is what writes
    the 'revealed' line in the access log.
    """

    _name = "drkds.vault.reveal"
    _description = "Reveal Vault Password"

    entry_id = fields.Many2one(
        "drkds.lite.vault.entry", string="Entry", required=True, readonly=True,
        ondelete="cascade",
    )
    entry_name = fields.Char(related="entry_id.name", string="Title", readonly=True)
    username = fields.Char(related="entry_id.username", readonly=True)
    secret = fields.Char(
        string="Password", readonly=True, exportable=False,
        help="Shown once, here. Closing this dialog discards it.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        wizards = super().create(vals_list)
        for wizard in wizards:
            # ``_read_secret`` enforces ownership and writes the access log.
            wizard.secret = wizard.entry_id._read_secret()
        return wizards

    def action_close(self):
        """Discard the plaintext held by this wizard and close the dialog."""
        self.sudo().write({"secret": False})
        return {"type": "ir.actions.act_window_close"}

    def name_get(self):
        return [(wizard.id, _("Reveal Password")) for wizard in self]
