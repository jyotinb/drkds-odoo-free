from odoo import _, fields, models
from odoo.exceptions import UserError


class DrkdsDocumentAddWizard(models.TransientModel):
    """File a selection of attachments into a folder, without copying them."""

    _name = "drkds.document.add.wizard"
    _description = "Add Attachments to Documents"

    folder_id = fields.Many2one("drkds.document.folder", string="Folder", required=True)
    tag_ids = fields.Many2many("drkds.document.tag", string="Tags")
    attachment_ids = fields.Many2many("ir.attachment", string="Attachments", required=True)

    def action_add(self):
        self.ensure_one()
        Document = self.env["drkds.document"]
        attachments = self.attachment_ids
        attachments.check_access("read")
        already = Document.sudo().search([("attachment_id", "in", attachments.ids)])
        done = set(already.mapped("attachment_id").ids)
        vals_list = []
        for attachment in attachments:
            if attachment.id in done:
                continue
            vals = {
                "name": attachment.name,
                "folder_id": self.folder_id.id,
                "attachment_id": attachment.id,
                "tag_ids": [(6, 0, self.tag_ids.ids)],
                "res_model": attachment.res_model or False,
                "res_id": attachment.res_id or False,
            }
            if self.folder_id.company_id:
                vals["company_id"] = self.folder_id.company_id.id
            if attachment.res_model and attachment.res_id and attachment.res_model in self.env:
                record = self.env[attachment.res_model].browse(attachment.res_id)
                if record.exists():
                    # The folder chosen wins over the record's company; the
                    # record's contact is kept only where it fits.
                    link_values, _fits = Document._values_from_record(
                        record, self.folder_id, self.env.company,
                    )
                    vals.update(link_values)
            vals_list.append(vals)
        if not vals_list:
            raise UserError(_("Every selected attachment is already filed as a document."))
        documents = Document.create(vals_list)
        action = self.env["ir.actions.act_window"]._for_xml_id("drkds_documents_lite.action_drkds_document")
        action["domain"] = [("id", "in", documents.ids)]
        action["context"] = {}
        return action
