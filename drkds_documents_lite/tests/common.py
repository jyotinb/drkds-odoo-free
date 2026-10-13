import base64

from odoo.tests import TransactionCase, new_test_user

# A 1x1 PNG, the smallest real image we can file.
PNG_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
PDF_MIN = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"


class DocumentsCommon(TransactionCase):
    """A manager, a clerk with document access, a member of the Legal group,
    and an outsider with no document access at all. The clerk and the outsider
    are contact managers so they can post in a partner's chatter."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Folder = cls.env["drkds.document.folder"]
        cls.Document = cls.env["drkds.document"]
        cls.Tag = cls.env["drkds.document.tag"]

        cls.legal_group = cls.env["res.groups"].create({"name": "Legal Team (test)"})

        cls.manager = new_test_user(
            cls.env, login="drkds_docl_manager", name="Docs Manager",
            groups="base.group_user,drkds_documents_lite.group_document_manager",
        )
        cls.clerk = new_test_user(
            cls.env, login="drkds_docl_clerk", name="Clerk",
            groups="base.group_user,base.group_partner_manager,drkds_documents_lite.group_document_user",
        )
        cls.lawyer = new_test_user(
            cls.env, login="drkds_docl_lawyer", name="Lawyer",
            groups="base.group_user,base.group_partner_manager,drkds_documents_lite.group_document_user",
        )
        cls.lawyer.write({"group_ids": [(4, cls.legal_group.id)]})
        cls.outsider = new_test_user(
            cls.env, login="drkds_docl_outsider", name="Outsider",
            groups="base.group_user,base.group_partner_manager",
        )

        cls.folder_general = cls.Folder.create({"name": "General"})
        cls.folder_legal = cls.Folder.create({
            "name": "Legal",
            "read_group_ids": [(6, 0, cls.legal_group.ids)],
        })
        cls.tag_signed = cls.Tag.create({"name": "Signed"})
        cls.partner = cls.env["res.partner"].create({"name": "Mehta Traders"})

    def _document(self, user=None, **vals):
        values = {
            "name": "Rent agreement",
            "folder_id": self.folder_general.id,
            "file": base64.b64encode(PDF_MIN),
            "file_name": "rent_agreement.pdf",
        }
        values.update(vals)
        model = self.Document.with_user(user) if user else self.Document
        return model.create(values)

    def _activities(self, record):
        return self.env["mail.activity"].search([
            ("res_model", "=", record._name), ("res_id", "=", record.id),
        ])
