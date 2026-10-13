import base64

from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import PDF_MIN, PNG_1x1, DocumentsCommon


@tagged("post_install", "-at_install")
class TestMirror(DocumentsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model_partner = cls.env["ir.model"]._get("res.partner")

    def _enable(self, *models):
        settings = self.env["res.config.settings"].create({
            "drkds_document_mirror_model_ids": [(6, 0, [m.id for m in models])],
        })
        settings.execute()

    def _post_with_files(self, record, user=None, files=(("scan.pdf", PDF_MIN),)):
        record = record.with_user(user) if user else record
        return record.message_post(
            body="Please find attached.",
            attachments=[(name, data) for name, data in files],
            message_type="comment",
        )

    def test_settings_create_a_folder_per_model(self):
        self._enable(self.model_partner)
        folder = self.Folder.search([("model_id", "=", self.model_partner.id)])
        self.assertEqual(len(folder), 1)
        self.assertEqual(folder.complete_name, "Linked Records / Contact")
        self.assertEqual(self.env["res.config.settings"].get_values()["drkds_document_mirror_model_ids"],
                         [(6, 0, [self.model_partner.id])])
        # Switching the model off keeps the folder but detaches it.
        self._enable()
        self.assertTrue(folder.exists())
        self.assertFalse(folder.model_id)
        # Switching it on again reuses the same folder rather than making a twin.
        self._enable(self.model_partner)
        self.assertEqual(self.Folder.search([("model_id", "=", self.model_partner.id)]), folder)

    def test_nothing_is_mirrored_until_configured(self):
        self._post_with_files(self.partner)
        self.assertFalse(self.Document.search([("res_model", "=", "res.partner")]))

    def test_chatter_file_is_mirrored_with_links(self):
        self._enable(self.model_partner)
        folder = self.Folder.search([("model_id", "=", self.model_partner.id)])
        message = self._post_with_files(self.partner, user=self.clerk,
                                        files=(("scan.pdf", PDF_MIN), ("photo.png", PNG_1x1)))
        docs = self.Document.search([("res_model", "=", "res.partner"), ("res_id", "=", self.partner.id)])
        self.assertEqual(len(docs), 2)
        self.assertEqual(set(docs.mapped("attachment_id").ids), set(message.attachment_ids.ids))
        self.assertEqual(docs.mapped("folder_id"), folder)
        self.assertEqual(docs.mapped("partner_id"), self.partner)
        self.assertEqual(docs.mapped("user_id"), self.clerk)
        self.assertEqual(sorted(docs.mapped("name")), ["photo.png", "scan.pdf"])
        self.assertEqual(sorted(docs.mapped("mimetype")), ["application/pdf", "image/png"])
        # The file was linked, not copied: still exactly two attachments.
        self.assertEqual(len(message.attachment_ids), 2)
        for doc in docs:
            self.assertEqual(doc.attachment_id.res_model, "res.partner")

    def test_a_poster_without_document_access_still_gets_mirrored(self):
        self._enable(self.model_partner)
        self._post_with_files(self.partner, user=self.outsider)
        docs = self.Document.search([("res_id", "=", self.partner.id), ("res_model", "=", "res.partner")])
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs.user_id, self.outsider)

    def test_same_attachment_is_never_mirrored_twice(self):
        self._enable(self.model_partner)
        message = self._post_with_files(self.partner)
        attachment = message.attachment_ids
        # A second message re-using the same attachment id.
        self.partner.message_post(body="again", attachment_ids=attachment.ids, message_type="comment")
        self.assertEqual(len(self.Document.search([("attachment_id", "=", attachment.id)])), 1)

    def test_message_without_files_creates_nothing(self):
        self._enable(self.model_partner)
        self.partner.message_post(body="just words", message_type="comment")
        self.assertFalse(self.Document.search([("res_model", "=", "res.partner")]))

    def test_other_models_are_untouched(self):
        self._enable(self.model_partner)
        doc = self._document()
        doc.message_post(body="file on a document", attachments=[("x.pdf", PDF_MIN)], message_type="comment")
        self.assertFalse(self.Document.search([("res_model", "=", "drkds.document")]))

    def test_deleting_a_mirrored_document_keeps_the_chatter_file(self):
        self._enable(self.model_partner)
        message = self._post_with_files(self.partner)
        attachment = message.attachment_ids
        doc = self.Document.search([("attachment_id", "=", attachment.id)])
        doc.unlink()
        self.assertTrue(attachment.exists())
        self.assertEqual(attachment.raw, PDF_MIN)

    def test_mirrored_document_takes_the_record_company(self):
        self._enable(self.model_partner)
        other = self.env["res.company"].create({"name": "Second Co"})
        self.partner.company_id = other
        self._post_with_files(self.partner)
        doc = self.Document.search([("res_id", "=", self.partner.id), ("res_model", "=", "res.partner")])
        self.assertEqual(doc.company_id, other)

    # -- side effects of a post must never break the post ----------------------
    def test_a_record_of_another_company_is_not_filed_in_a_company_folder(self):
        """The mirror folder is kept for this company; a contact of another
        company posts fine and is simply not mirrored there."""
        self._enable(self.model_partner)
        folder = self.Folder.search([("model_id", "=", self.model_partner.id)])
        folder.company_id = self.env.company
        other = self.env["res.company"].create({"name": "Second Co"})
        self.outsider.company_ids = [(4, other.id)]
        self.partner.company_id = other
        record = self.partner.with_context(allowed_company_ids=[other.id, self.env.company.id])
        message = self._post_with_files(record, user=self.outsider)
        self.assertEqual(len(message.attachment_ids), 1)
        self.assertFalse(self.Document.search([("res_model", "=", "res.partner"), ("res_id", "=", self.partner.id)]))
        # A contact of this company still is.
        mine = self.env["res.partner"].create({"name": "Local Traders", "company_id": self.env.company.id})
        self._post_with_files(mine, user=self.outsider)
        doc = self.Document.search([("res_model", "=", "res.partner"), ("res_id", "=", mine.id)])
        self.assertEqual((doc.company_id, doc.partner_id), (self.env.company, mine))

    def test_add_to_documents_into_a_folder_of_another_company(self):
        """The folder chosen wins; a contact of another company is left off
        rather than failing the company check."""
        other = self.env["res.company"].create({"name": "Second Co"})
        supplier = self.env["res.partner"].create({"name": "Far Supplier", "company_id": other.id})
        attachment = self.env["ir.attachment"].create({
            "name": "quote.pdf", "raw": PDF_MIN, "res_model": "res.partner", "res_id": supplier.id,
        })
        head_office = self.Folder.create({"name": "Head office", "company_id": self.env.company.id})
        wizard = self.env["drkds.document.add.wizard"].create({
            "folder_id": head_office.id, "attachment_ids": [(6, 0, attachment.ids)],
        })
        doc = self.Document.search(wizard.action_add()["domain"])
        self.assertEqual(doc.company_id, self.env.company)
        self.assertFalse(doc.partner_id)
        self.assertEqual((doc.res_model, doc.res_id), ("res.partner", supplier.id))

    # -- who hears about a mirrored document -----------------------------------
    def test_a_poster_without_document_access_is_not_made_a_follower(self):
        self._enable(self.model_partner)
        self._post_with_files(self.partner, user=self.outsider)
        doc = self.Document.search([("res_model", "=", "res.partner"), ("res_id", "=", self.partner.id)])
        self.assertEqual(doc.user_id, self.outsider)
        self.assertNotIn(self.outsider.partner_id, doc.message_partner_ids)
        remark = doc.with_user(self.manager).message_post(
            body="Internal remark on this contract", message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        notified = self.env["mail.notification"].search([("mail_message_id", "=", remark.id)])
        self.assertNotIn(self.outsider.partner_id, notified.res_partner_id)

    def test_a_poster_outside_the_mirror_folder_groups_is_not_made_a_follower(self):
        self._enable(self.model_partner)
        folder = self.Folder.search([("model_id", "=", self.model_partner.id)])
        folder.read_group_ids = [(6, 0, self.legal_group.ids)]
        self._post_with_files(self.partner, user=self.clerk)
        doc = self.Document.search([("res_model", "=", "res.partner"), ("res_id", "=", self.partner.id)])
        self.assertEqual(len(doc), 1)
        self.assertNotIn(self.clerk.partner_id, doc.message_partner_ids)
        # A poster who can open it follows it as its owner.
        self._post_with_files(self.partner, user=self.lawyer, files=(("lease.pdf", PDF_MIN),))
        lease = self.Document.search([("name", "=", "lease.pdf")])
        self.assertIn(self.lawyer.partner_id, lease.message_partner_ids)

    def test_add_to_documents_proposes_only_a_folder_the_user_can_see(self):
        self._enable(self.model_partner)
        folder = self.Folder.search([("model_id", "=", self.model_partner.id)])
        folder.read_group_ids = [(6, 0, self.legal_group.ids)]
        attachment = self.env["ir.attachment"].create({
            "name": "card.pdf", "raw": PDF_MIN, "res_model": "res.partner", "res_id": self.partner.id,
        })
        self.env.invalidate_all()
        for user, expected in ((self.clerk, False), (self.lawyer, folder.id)):
            action = attachment.with_user(user).action_drkds_add_to_documents()
            self.assertEqual(action["context"]["default_folder_id"], expected, user.login)
        # Someone without document rights learns nothing about the folders.
        with self.assertRaises(AccessError):
            attachment.with_user(self.outsider).action_drkds_add_to_documents()
