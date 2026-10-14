from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import DocumentsCommon


@tagged("post_install", "-at_install")
class TestFolder(DocumentsCommon):
    def test_app_menu_uses_the_module_title(self):
        """The app menu carries the module's own title, never the name of an
        Odoo Enterprise app (project rule on naming)."""
        root = self.env.ref("drkds_documents_lite.menu_drkds_documents_root")
        self.assertEqual(root.with_context(lang="en_US").name, "Document Folders")

    def test_complete_name_follows_the_tree(self):
        contracts = self.Folder.create({"name": "Contracts", "parent_id": self.folder_legal.id})
        year = self.Folder.create({"name": "2026", "parent_id": contracts.id})
        self.assertEqual(year.complete_name, "Legal / Contracts / 2026")
        self.folder_legal.name = "Legal Dept"
        self.assertEqual(year.complete_name, "Legal Dept / Contracts / 2026")

    def test_sub_folder_inherits_parent_groups(self):
        contracts = self.Folder.create({"name": "Contracts", "parent_id": self.folder_legal.id})
        self.assertEqual(contracts.read_group_ids, self.legal_group)
        open_child = self.Folder.create({"name": "Open", "parent_id": self.folder_general.id})
        self.assertFalse(open_child.read_group_ids)

    def test_folder_cannot_be_its_own_ancestor(self):
        contracts = self.Folder.create({"name": "Contracts", "parent_id": self.folder_legal.id})
        # The ORM's parent-store refuses the cycle before any constraint runs.
        with self.assertRaises(UserError):
            self.folder_legal.parent_id = contracts

    def test_one_folder_per_mirrored_model(self):
        model = self.env["ir.model"]._get("res.partner")
        self.folder_general.model_id = model
        from odoo.tools import mute_logger
        from psycopg2.errors import UniqueViolation
        with mute_logger("odoo.sql_db"), self.assertRaises(UniqueViolation):
            self.Folder.create({"name": "Second partner folder", "model_id": model.id})

    # -- rights ---------------------------------------------------------
    def test_restricted_folder_is_invisible_to_a_user_outside_its_groups(self):
        visible = self.Folder.with_user(self.clerk).search([])
        self.assertIn(self.folder_general, visible)
        self.assertNotIn(self.folder_legal, visible)
        with self.assertRaises(AccessError):
            self.folder_legal.with_user(self.clerk).read(["name"])

    def test_restricted_folder_is_visible_to_its_group_and_to_managers(self):
        self.assertIn(self.folder_legal, self.Folder.with_user(self.lawyer).search([]))
        self.assertIn(self.folder_legal, self.Folder.with_user(self.manager).search([]))

    def test_documents_follow_their_folder(self):
        secret = self._document(name="NDA", folder_id=self.folder_legal.id)
        public = self._document(name="Canteen menu")
        clerk_docs = self.Document.with_user(self.clerk).search([])
        self.assertIn(public, clerk_docs)
        self.assertNotIn(secret, clerk_docs)
        with self.assertRaises(AccessError):
            secret.with_user(self.clerk).read(["name"])
        self.assertIn(secret, self.Document.with_user(self.lawyer).search([]))

    def test_write_groups_decide_who_may_change_documents(self):
        self.folder_general.write_group_ids = [(6, 0, self.legal_group.ids)]
        doc = self._document(name="Policy")
        # Readable by the clerk, but not writable.
        self.assertEqual(doc.with_user(self.clerk).name, "Policy")
        with self.assertRaises(AccessError):
            doc.with_user(self.clerk).write({"name": "Policy v2"})
        with self.assertRaises(AccessError):
            self._document(user=self.clerk, name="Clerk's file")
        with self.assertRaises(AccessError):
            doc.with_user(self.clerk).unlink()
        # The lawyer is in the write group.
        doc.with_user(self.lawyer).write({"name": "Policy v2"})
        self.assertEqual(doc.name, "Policy v2")
        mine = self._document(user=self.lawyer, name="Lawyer's file")
        self.assertEqual(mine.user_id, self.lawyer)

    def test_no_write_group_means_every_reader_may_write(self):
        doc = self._document(user=self.clerk, name="Clerk's file")
        doc.with_user(self.clerk).write({"description": "updated"})
        self.assertEqual(doc.description, "updated")

    def test_users_cannot_create_folders_or_tags(self):
        with self.assertRaises(AccessError):
            self.Folder.with_user(self.clerk).create({"name": "Mine"})
        with self.assertRaises(AccessError):
            self.Tag.with_user(self.clerk).create({"name": "Mine"})
        self.assertEqual(self.Tag.with_user(self.clerk).search([("name", "=", "Signed")]), self.tag_signed)

    def test_outsider_has_no_access_at_all(self):
        with self.assertRaises(AccessError):
            self.Document.with_user(self.outsider).search([])

    def test_folder_with_documents_cannot_be_deleted(self):
        self._document()
        from odoo.tools import mute_logger
        from psycopg2.errors import ForeignKeyViolation
        with mute_logger("odoo.sql_db"), self.assertRaises(ForeignKeyViolation):
            self.folder_general.unlink()

    def test_document_counts(self):
        contracts = self.Folder.create({"name": "Contracts", "parent_id": self.folder_legal.id})
        self._document(folder_id=self.folder_legal.id)
        self._document(folder_id=contracts.id)
        self._document(folder_id=contracts.id)
        self.assertEqual(self.folder_legal.document_count, 1)
        self.assertEqual(self.folder_legal.document_count_total, 3)
        self.assertEqual(contracts.document_count, 2)

    # -- a change of groups reaches the branch ----------------------------------
    def test_restricting_a_folder_restricts_the_sub_folders_that_followed_it(self):
        """Sub-folders made before the parent was restricted carried the
        parent's old (open) lists; they follow the change. A sub-folder given
        lists of its own keeps them."""
        hr = self.Folder.create({"name": "HR"})
        payroll = self.Folder.create({"name": "Payroll", "parent_id": hr.id})
        year = self.Folder.create({"name": "2026", "parent_id": payroll.id})
        old_year = self.Folder.create({"name": "2025", "parent_id": payroll.id})
        old_year.active = False
        everyone = self.env.ref("base.group_user")
        notices = self.Folder.create({
            "name": "Notices", "parent_id": hr.id, "read_group_ids": [(6, 0, everyone.ids)],
        })
        open_under_notices = self.Folder.create({
            "name": "Canteen", "parent_id": notices.id, "read_group_ids": [(5,)],
        })
        payslip = self._document(name="Payslip", folder_id=year.id)

        hr.read_group_ids = [(6, 0, self.legal_group.ids)]

        self.assertEqual(payroll.read_group_ids, self.legal_group)
        self.assertEqual(year.read_group_ids, self.legal_group)
        self.assertEqual(old_year.read_group_ids, self.legal_group, "archived folders follow too")
        self.assertEqual(notices.read_group_ids, everyone, "its own list is kept")
        self.assertFalse(open_under_notices.read_group_ids,
                         "below a folder with its own list nothing is inherited from higher up")
        self.env.invalidate_all()
        self.assertNotIn(payslip, self.Document.with_user(self.clerk).search([]))
        self.assertNotIn(year, self.Folder.with_user(self.clerk).search([]))
        self.assertIn(payslip, self.Document.with_user(self.lawyer).search([]))

        # Write groups follow the same path, and so does opening up again.
        hr.write_group_ids = [(6, 0, self.legal_group.ids)]
        self.assertEqual(year.write_group_ids, self.legal_group)
        self.assertEqual(notices.write_group_ids, self.legal_group,
                         "Notices had the same (empty) write list as HR, so it followed")
        hr.read_group_ids = [(5,)]
        self.assertFalse(payroll.read_group_ids)
        self.assertFalse(year.read_group_ids)
        self.assertEqual(notices.read_group_ids, everyone)

    # -- tags ------------------------------------------------------------------
    def test_a_new_tag_shows_on_kanban_cards(self):
        """The Kanban many2many_tags widget hides tags of colour 0."""
        tags = self.Tag.create([{"name": f"Tag {i}"} for i in range(30)])
        self.assertTrue(all(1 <= tag.color <= 11 for tag in tags), tags.mapped("color"))
