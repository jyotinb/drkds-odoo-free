import base64

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
