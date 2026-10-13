from odoo import models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def action_drkds_add_to_documents(self):
        """Open the Add to Documents wizard on the selected attachments.

        This is the target of the server action bound to attachment lists.
        """
        folder = self.env["drkds.document.folder"]
        models_ = set(self.mapped("res_model")) - {False}
        if len(models_) == 1:
            # Proposed with the user's own rights: a folder they cannot see
            # is not offered (nor named) to them.
            # ir.model itself is unreadable to plain users, so the model id is
            # resolved first.
            model_id = self.env["ir.model"]._get_id(models_.pop())
            folder = folder.search([("model_id", "=", model_id)], limit=1)
        return {
            "type": "ir.actions.act_window",
            "name": "Add to Documents",
            "res_model": "drkds.document.add.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_attachment_ids": [(6, 0, self.ids)],
                "default_folder_id": folder.id,
            },
        }
