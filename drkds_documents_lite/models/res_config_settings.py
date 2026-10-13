from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    drkds_document_mirror_model_ids = fields.Many2many(
        "ir.model", "drkds_document_settings_mirror_model_rel", "settings_id", "model_id",
        string="Mirror Chatter Files Of",
        domain="[('is_mail_thread', '=', True), ('transient', '=', False)]",
        help="Files posted in the chatter of these models are filed as documents "
        "in a folder named after the model, under Linked Records.",
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        folders = self.env["drkds.document.folder"].sudo().with_context(active_test=False).search(
            [("model_id", "!=", False)]
        )
        res["drkds_document_mirror_model_ids"] = [(6, 0, folders.mapped("model_id").ids)]
        return res

    def set_values(self):
        super().set_values()
        Folder = self.env["drkds.document.folder"].sudo().with_context(active_test=False)
        wanted = self.drkds_document_mirror_model_ids
        current = Folder.search([("model_id", "!=", False)])
        # Dropped from the list: the folder and its documents stay, it just
        # stops receiving new files.
        current.filtered(lambda f: f.model_id not in wanted).write({"model_id": False})
        mirrored = current.mapped("model_id")
        root = self.env.ref("drkds_documents_lite.folder_linked_records", raise_if_not_found=False)
        for model in wanted - mirrored:
            folder = Folder.search(
                [("parent_id", "=", root.id if root else False), ("name", "=", model.name),
                 ("model_id", "=", False)], limit=1,
            )
            if folder:
                folder.write({"model_id": model.id, "active": True})
            else:
                Folder.create({
                    "name": model.name,
                    "parent_id": root.id if root else False,
                    "model_id": model.id,
                    "description": _("Files posted in the chatter of %s records.", model.name),
                })
