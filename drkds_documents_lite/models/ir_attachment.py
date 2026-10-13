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
            folder = folder._get_mirror_folder(models_.pop())
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
