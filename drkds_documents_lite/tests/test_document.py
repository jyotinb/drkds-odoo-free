import base64

from odoo.exceptions import AccessError
from odoo.tests import Form, tagged

from .common import PDF_MIN, PNG_1x1, DocumentsCommon


@tagged("post_install", "-at_install")
class TestDocument(DocumentsCommon):
    def test_upload_creates_an_owned_attachment(self):
        doc = self._document()
        att = doc.attachment_id
        self.assertTrue(att)
        self.assertEqual((att.res_model, att.res_id), ("drkds.document", doc.id))
        self.assertEqual(att.name, "rent_agreement.pdf")
        self.assertEqual(att.raw, PDF_MIN)
        self.assertEqual(doc.mimetype, "application/pdf")
        self.assertEqual(doc.file_size, len(PDF_MIN))
        self.assertEqual(doc.preview_kind, "pdf")
        self.assertEqual(doc.file_name, "rent_agreement.pdf")
        self.assertEqual(base64.b64decode(doc.file), PDF_MIN)

    def test_image_preview_kind(self):
        doc = self._document(file=base64.b64encode(PNG_1x1), file_name="logo.png")
        self.assertEqual(doc.mimetype, "image/png")
        self.assertEqual(doc.preview_kind, "image")
        self.assertEqual(doc.file_size, len(PNG_1x1))

    def test_document_without_file(self):
        doc = self.Document.create({"name": "Placeholder", "folder_id": self.folder_general.id})
        self.assertFalse(doc.attachment_id)
        self.assertEqual(doc.preview_kind, "none")
        self.assertEqual(doc.file_size, 0)

    def test_replacing_the_file_reuses_the_owned_attachment(self):
        doc = self._document()
        first = doc.attachment_id
        doc.write({"file": base64.b64encode(PNG_1x1), "file_name": "scan.png"})
        self.assertEqual(doc.attachment_id, first)
        self.assertEqual(first.mimetype, "image/png")
        self.assertEqual(first.name, "scan.png")

    def test_clearing_the_file_deletes_only_an_owned_attachment(self):
        doc = self._document()
        own = doc.attachment_id
        doc.file = False
        self.assertFalse(own.exists())
        self.assertFalse(doc.attachment_id)

        foreign = self.env["ir.attachment"].create({
            "name": "partner_card.pdf", "raw": PDF_MIN,
            "res_model": "res.partner", "res_id": self.partner.id,
        })
        doc.attachment_id = foreign
        self.assertEqual(doc.preview_kind, "pdf")
        doc.file = False
        self.assertTrue(foreign.exists(), "a borrowed file is never deleted")
        self.assertFalse(doc.attachment_id)

    def test_uploading_over_a_borrowed_file_makes_a_new_attachment(self):
        foreign = self.env["ir.attachment"].create({
            "name": "partner_card.pdf", "raw": PDF_MIN,
            "res_model": "res.partner", "res_id": self.partner.id,
        })
        doc = self.Document.create({
            "name": "Card", "folder_id": self.folder_general.id, "attachment_id": foreign.id,
        })
        doc.write({"file": base64.b64encode(PNG_1x1), "file_name": "new.png"})
        self.assertNotEqual(doc.attachment_id, foreign)
        self.assertEqual(foreign.raw, PDF_MIN, "the partner's file is untouched")
        self.assertEqual(doc.attachment_id.res_model, "drkds.document")

    def test_deleting_a_document_keeps_a_borrowed_file(self):
        foreign = self.env["ir.attachment"].create({
            "name": "partner_card.pdf", "raw": PDF_MIN,
            "res_model": "res.partner", "res_id": self.partner.id,
        })
        borrowed = self.Document.create({
            "name": "Card", "folder_id": self.folder_general.id, "attachment_id": foreign.id,
        })
        owned = self._document()
        own_att = owned.attachment_id
        (borrowed | owned).unlink()
        self.assertTrue(foreign.exists())
        self.assertFalse(own_att.exists())

    def test_linked_record_name_and_open(self):
        doc = self._document(res_model="res.partner", res_id=self.partner.id)
        self.assertEqual(doc.res_name, "Mehta Traders")
        action = doc.action_open_linked_record()
        self.assertEqual((action["res_model"], action["res_id"]), ("res.partner", self.partner.id))
        self.partner.name = "Mehta Traders Pvt Ltd"
        doc.invalidate_recordset(["res_name"])
        self.assertEqual(doc.res_name, "Mehta Traders Pvt Ltd")

    def test_linked_record_name_is_blank_when_record_is_gone(self):
        gone = self.env["res.partner"].create({"name": "Temporary"})
        doc = self._document(res_model="res.partner", res_id=gone.id)
        gone.unlink()
        doc.invalidate_recordset(["res_name"])
        self.assertFalse(doc.res_name)

    def test_form_defaults(self):
        f = Form(self.Document.with_user(self.clerk))
        f.name = "Form upload"
        f.folder_id = self.folder_general
        f.file = base64.b64encode(PDF_MIN)
        doc = f.save()
        self.assertEqual(doc.user_id, self.clerk)
        self.assertEqual(doc.company_id, self.env.company)
        self.assertEqual(doc.attachment_id.res_id, doc.id)
        self.assertTrue(doc.attachment_id.with_user(self.clerk).datas)

    def test_add_to_documents_wizard(self):
        att_a = self.env["ir.attachment"].create({
            "name": "a.pdf", "raw": PDF_MIN, "res_model": "res.partner", "res_id": self.partner.id,
        })
        att_b = self.env["ir.attachment"].create({
            "name": "b.png", "raw": PNG_1x1, "res_model": "res.partner", "res_id": self.partner.id,
        })
        action = (att_a | att_b).action_drkds_add_to_documents()
        self.assertEqual(action["res_model"], "drkds.document.add.wizard")
        wizard = self.env["drkds.document.add.wizard"].with_context(action["context"]).create({
            "folder_id": self.folder_general.id,
            "tag_ids": [(6, 0, self.tag_signed.ids)],
        })
        self.assertEqual(wizard.attachment_ids, att_a | att_b)
        result = wizard.action_add()
        docs = self.Document.search(result["domain"])
        self.assertEqual(len(docs), 2)
        self.assertEqual(set(docs.mapped("attachment_id").ids), {att_a.id, att_b.id})
        self.assertEqual(docs.mapped("partner_id"), self.partner)
        self.assertEqual(docs.mapped("res_model"), ["res.partner", "res.partner"])
        self.assertEqual(docs.mapped("tag_ids"), self.tag_signed)
        # Running it again files nothing twice.
        from odoo.exceptions import UserError
        again = self.env["drkds.document.add.wizard"].create({
            "folder_id": self.folder_general.id, "attachment_ids": [(6, 0, (att_a | att_b).ids)],
        })
        with self.assertRaises(UserError):
            again.action_add()

    def test_expiry_state_search(self):
        from datetime import timedelta
        from odoo import fields
        today = fields.Date.context_today(self.Document)
        expired = self._document(name="old", expiry_date=today - timedelta(days=1))
        today_doc = self._document(name="today", expiry_date=today)
        soon = self._document(name="soon", expiry_date=today + timedelta(days=7))
        later = self._document(name="later", expiry_date=today + timedelta(days=8))
        none = self._document(name="none")
        self.assertEqual(expired.expiry_state, "expired")
        self.assertEqual(today_doc.expiry_state, "soon", "expiring today is not yet expired")
        self.assertEqual(soon.expiry_state, "soon")
        self.assertEqual(later.expiry_state, "ok")
        self.assertEqual(none.expiry_state, "none")
        self.assertEqual(self.Document.search([("expiry_state", "=", "soon")]), today_doc | soon)
        self.assertEqual(self.Document.search([("expiry_state", "in", ["expired", "ok"])]), expired | later)
        self.assertEqual(
            self.Document.search([("expiry_state", "!=", "none"), ("id", "in", (expired | later | none).ids)]),
            expired | later,
        )

    # -- files the reader cannot open -----------------------------------------
    def _private_attachment(self, user):
        """A file ``user`` uploaded without attaching it to any record: base
        lets only its creator (and administrators) read it."""
        return self.env["ir.attachment"].with_user(user).create({
            "name": "private.pdf", "raw": PDF_MIN,
        }).sudo()

    def test_a_document_whose_file_the_reader_cannot_open_still_opens(self):
        """A document in an open folder may point at a file that belongs to a
        record the reader cannot open (a mirrored chatter file, a filed
        attachment). The file stays closed; the document, the Kanban and the
        form must not fail."""
        attachment = self._private_attachment(self.lawyer)
        doc = self.Document.create({
            "name": "Lawyer's scan", "folder_id": self.folder_general.id,
            "attachment_id": attachment.id,
        })
        self.env.invalidate_all()
        values = doc.with_user(self.clerk).read(
            ["name", "preview_kind", "mimetype", "file_size", "file", "file_name"])[0]
        self.assertEqual(values["preview_kind"], "restricted")
        self.assertFalse(values["file"])
        self.assertFalse(values["file_name"])
        self.assertEqual(values["mimetype"], "application/pdf")
        self.assertEqual(values["file_size"], len(PDF_MIN))
        # The Kanban over the folder loads, this card included.
        self.env.invalidate_all()
        cards = self.Document.with_user(self.clerk).web_search_read(
            [("folder_id", "=", self.folder_general.id)],
            {"name": {}, "preview_kind": {}, "mimetype": {}, "attachment_id": {}},
        )["records"]
        self.assertIn(doc.id, [card["id"] for card in cards])
        # The form opens.
        self.env.invalidate_all()
        self.assertEqual(Form(doc.with_user(self.clerk)).name, "Lawyer's scan")
        # The file itself is still out of reach.
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            attachment.with_user(self.clerk).read(["datas"])
        # Its owner reads it through the same document, in the same transaction.
        lawyer_doc = doc.with_user(self.lawyer)
        self.assertEqual(lawyer_doc.preview_kind, "pdf")
        self.assertEqual(base64.b64decode(lawyer_doc.file), PDF_MIN)
        self.assertEqual(lawyer_doc.file_name, "private.pdf")

    def test_a_document_cannot_point_at_a_file_its_author_cannot_read(self):
        attachment = self._private_attachment(self.lawyer)
        with self.assertRaises(AccessError):
            self.Document.with_user(self.clerk).create({
                "name": "Borrowed", "folder_id": self.folder_general.id,
                "attachment_id": attachment.id,
            })
        doc = self._document(user=self.clerk)
        with self.assertRaises(AccessError):
            doc.with_user(self.clerk).write({"attachment_id": attachment.id})
        # A file the clerk can read may be linked.
        card = self.env["ir.attachment"].create({
            "name": "card.pdf", "raw": PDF_MIN,
            "res_model": "res.partner", "res_id": self.partner.id,
        })
        doc.with_user(self.clerk).write({"attachment_id": card.id})
        self.assertEqual(doc.attachment_id, card)

    # -- moving --------------------------------------------------------------
    def test_a_document_cannot_be_moved_where_its_mover_may_not_file(self):
        """Record rules are checked against the values before a write, so the
        destination needs a check of its own."""
        policies = self.Folder.create({
            "name": "Policies", "write_group_ids": [(6, 0, self.legal_group.ids)],
        })
        other_company = self.env["res.company"].create({"name": "Other Co"})
        doc = self._document(user=self.clerk)
        with self.assertRaises(AccessError):
            doc.with_user(self.clerk).write({"folder_id": policies.id})
        with self.assertRaises(AccessError):
            doc.with_user(self.clerk).write({"folder_id": self.folder_legal.id})
        with self.assertRaises(AccessError):
            doc.with_user(self.clerk).write({"company_id": other_company.id})
        self.assertEqual(doc.folder_id, self.folder_general)
        self.assertEqual(doc.company_id, self.env.company)
        # Someone in the write group may move it there.
        doc.with_user(self.lawyer).write({"folder_id": policies.id})
        self.assertEqual(doc.folder_id, policies)

    # -- followers -----------------------------------------------------------
    def test_an_owner_who_cannot_read_the_document_is_not_subscribed(self):
        """A follower receives every message posted on the document, so an
        owner outside the folder's groups must not become one."""
        doc = self.Document.with_user(self.manager).create({
            "name": "NDA", "folder_id": self.folder_legal.id, "user_id": self.clerk.id,
        })
        self.assertEqual(doc.user_id, self.clerk)
        self.assertNotIn(self.clerk.partner_id, doc.message_partner_ids)
        doc.with_user(self.manager).user_id = self.lawyer
        self.assertIn(self.lawyer.partner_id, doc.message_partner_ids)

    # -- uninstall -----------------------------------------------------------
    def test_uninstall_hook_frees_the_files_of_every_model_of_the_module(self):
        """Mail deletes every attachment that names a model being removed.
        Whatever this module's models own is freed first, so it survives."""
        from odoo.addons.drkds_documents_lite import uninstall_hook

        doc = self._document()
        own = doc.attachment_id
        chatter = doc.message_post(body="signed copy", attachments=[("signed.pdf", PDF_MIN)]).attachment_ids
        Attachment = self.env["ir.attachment"]
        on_folder = Attachment.create({
            "name": "folder.pdf", "raw": PDF_MIN,
            "res_model": "drkds.document.folder", "res_id": self.folder_general.id,
        })
        on_tag = Attachment.create({
            "name": "tag.png", "raw": PNG_1x1,
            "res_model": "drkds.document.tag", "res_id": self.tag_signed.id,
        })
        on_partner = Attachment.create({
            "name": "card.pdf", "raw": PDF_MIN,
            "res_model": "res.partner", "res_id": self.partner.id,
        })
        self.Document.create({"name": "Card", "folder_id": self.folder_general.id,
                              "attachment_id": on_partner.id})

        uninstall_hook(self.env)

        self.assertFalse(self.Document.with_context(active_test=False).search([]))
        for attachment in (own, chatter, on_folder, on_tag):
            self.assertTrue(attachment.exists(), attachment.name)
            self.assertFalse(attachment.res_model, attachment.name)
        self.assertEqual((on_partner.res_model, on_partner.res_id), ("res.partner", self.partner.id))
        self.assertFalse(Attachment.search([
            ("res_model", "in", ["drkds.document", "drkds.document.folder", "drkds.document.tag"]),
        ]))
