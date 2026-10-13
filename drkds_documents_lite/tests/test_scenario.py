"""End to end: a manager sets up two folders, one of them restricted to the
Legal group, five files are filed, a clerk sees only the open folder, and the
expiry job reminds the owner of the one file that is about to lapse."""
import base64
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import Form, tagged

from .common import PDF_MIN, PNG_1x1, DocumentsCommon


@tagged("post_install", "-at_install")
class TestDocumentsScenario(DocumentsCommon):
    def test_two_folders_five_files(self):
        today = fields.Date.today()
        manager_env = self.env(user=self.manager)

        # 1. The manager makes two folders: Operations, open to all, and
        #    Legal / Contracts under the restricted Legal folder.
        operations = manager_env["drkds.document.folder"].create({"name": "Operations"})
        contracts = manager_env["drkds.document.folder"].create({
            "name": "Contracts", "parent_id": self.folder_legal.id,
        })
        self.assertEqual(contracts.complete_name, "Legal / Contracts")
        self.assertEqual(contracts.read_group_ids, self.legal_group, "inherited from Legal")

        # 2. Three files go into Operations through the form, as a clerk
        #    would file them: a licence that expires in 5 days, a tagged
        #    photo, and a policy with no expiry.
        clerk_env = self.env(user=self.clerk)
        f = Form(clerk_env["drkds.document"])
        f.name = "Shop and Establishment Licence"
        f.folder_id = operations
        f.file = base64.b64encode(PDF_MIN)
        f.expiry_date = today + timedelta(days=5)
        f.partner_id = self.partner
        licence = f.save()

        f = Form(clerk_env["drkds.document"])
        f.name = "Warehouse photo"
        f.folder_id = operations
        f.file = base64.b64encode(PNG_1x1)
        f.tag_ids.add(self.tag_signed)
        photo = f.save()

        policy = clerk_env["drkds.document"].create({
            "name": "Leave policy", "folder_id": operations.id,
            "file": base64.b64encode(PDF_MIN), "file_name": "leave_policy.pdf",
            "expiry_date": today + timedelta(days=90),
        })

        # 3. Two contracts go into the restricted folder, filed by the lawyer.
        lawyer_env = self.env(user=self.lawyer)
        nda = lawyer_env["drkds.document"].create({
            "name": "NDA Mehta Traders", "folder_id": contracts.id,
            "file": base64.b64encode(PDF_MIN), "file_name": "nda.pdf",
            "partner_id": self.partner.id, "expiry_date": today + timedelta(days=2),
        })
        lease = lawyer_env["drkds.document"].create({
            "name": "Office lease", "folder_id": contracts.id,
            "file": base64.b64encode(PDF_MIN), "file_name": "lease.pdf",
        })

        # Every file became exactly one attachment owned by its document.
        for doc in (licence, photo, policy, nda, lease):
            self.assertEqual(doc.attachment_id.res_model, "drkds.document")
            self.assertEqual(doc.attachment_id.res_id, doc.id)
        # The form only sets the binary; the file takes the document's name.
        self.assertEqual(licence.attachment_id.name, "Shop and Establishment Licence")
        self.assertEqual(policy.attachment_id.name, "leave_policy.pdf")
        self.assertEqual(licence.mimetype, "application/pdf")
        self.assertEqual(photo.mimetype, "image/png")
        self.assertEqual(photo.preview_kind, "image")
        self.assertEqual(licence.user_id, self.clerk)
        self.assertEqual(nda.user_id, self.lawyer)
        self.assertEqual(operations.document_count, 3)
        self.assertEqual(self.folder_legal.document_count_total, 2)

        # 4. Visibility. The clerk sees Operations and its three files, and
        #    neither Legal nor Contracts nor anything in them.
        clerk_folders = clerk_env["drkds.document.folder"].search([])
        self.assertIn(operations, clerk_folders)
        self.assertNotIn(self.folder_legal, clerk_folders)
        self.assertNotIn(contracts, clerk_folders)
        clerk_docs = clerk_env["drkds.document"].search([("id", "in", (licence | photo | policy | nda | lease).ids)])
        self.assertEqual(clerk_docs, licence | photo | policy)
        with self.assertRaises(AccessError):
            nda.with_user(self.clerk).read(["name"])
        with self.assertRaises(AccessError):
            nda.attachment_id.with_user(self.clerk).read(["datas"])
        #    The lawyer and the manager see all five.
        all_ids = (licence | photo | policy | nda | lease).ids
        self.assertEqual(len(lawyer_env["drkds.document"].search([("id", "in", all_ids)])), 5)
        self.assertEqual(len(manager_env["drkds.document"].search([("id", "in", all_ids)])), 5)
        self.assertTrue(nda.attachment_id.with_user(self.lawyer).datas)

        # 5. Search answers the questions people ask.
        self.assertEqual(
            manager_env["drkds.document"].search([("tag_ids", "in", self.tag_signed.ids), ("id", "in", all_ids)]),
            photo,
        )
        self.assertEqual(
            manager_env["drkds.document"].search([("partner_id", "=", self.partner.id), ("id", "in", all_ids)]),
            licence | nda,
        )
        self.assertEqual(
            manager_env["drkds.document"].search([("folder_id", "child_of", self.folder_legal.id)]),
            nda | lease,
        )
        self.assertEqual(
            manager_env["drkds.document"].search([("expiry_state", "=", "soon"), ("id", "in", all_ids)]),
            licence | nda,
        )

        # 6. The nightly job: the licence (5 days) and the NDA (2 days) get a
        #    to-do for their owners; the policy (90 days) does not. Running
        #    it again the same day adds nothing.
        reminded = self.Document._cron_drkds_expiry_reminder()
        self.assertEqual(reminded, licence | nda)
        self.assertEqual(self._activities(licence).user_id, self.clerk)
        self.assertEqual(self._activities(licence).date_deadline, today + timedelta(days=5))
        self.assertEqual(self._activities(nda).user_id, self.lawyer)
        self.assertFalse(self._activities(policy))
        self.assertFalse(self.Document._cron_drkds_expiry_reminder())
        self.assertEqual(len(self._activities(licence)), 1)

        # 7. The clerk renews the licence: new expiry, new reminder later on.
        licence.with_user(self.clerk).write({"expiry_date": today + timedelta(days=365)})
        self.assertEqual(licence.expiry_state, "ok")
        self.assertFalse(self.Document._cron_drkds_expiry_reminder())

        # 8. Deleting the photo removes its own attachment; nothing else moves.
        photo_att = photo.attachment_id
        photo.with_user(self.clerk).unlink()
        self.assertFalse(photo_att.exists())
        self.assertEqual(operations.document_count, 2)
        self.assertTrue(licence.attachment_id.exists())
