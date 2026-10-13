from odoo import models


class MailThread(models.AbstractModel):
    """Mirror chatter attachments into the folder configured for the model."""

    _inherit = "mail.thread"

    def _message_post_after_hook(self, message, msg_values):
        result = super()._message_post_after_hook(message, msg_values)
        attachments = message.attachment_ids
        if attachments and not self.env.context.get("drkds_skip_document_mirror"):
            folder = self.env["drkds.document.folder"]._get_mirror_folder(self._name)
            if folder:
                self.env["drkds.document"]._mirror_attachments(self, attachments, folder)
        return result
