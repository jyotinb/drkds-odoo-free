from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestKbSecurity(TransactionCase):
    """Two groups, enforced by access rights and record rules."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Article = cls.env["drkds.lite.kb.article"]
        cls.reader = new_test_user(
            cls.env, login="kb_reader",
            groups="base.group_user,drkds_knowledge_base_lite.group_kb_reader",
        )
        cls.editor = new_test_user(
            cls.env, login="kb_editor",
            groups="base.group_user,drkds_knowledge_base_lite.group_kb_editor",
        )
        cls.section = cls.env["drkds.lite.kb.section"].create({"name": "Handbook"})
        cls.published = cls.Article.create({
            "name": "Published article", "section_id": cls.section.id,
            "body": "<p>visible to everyone</p>", "state": "published",
        })
        cls.draft = cls.Article.create({
            "name": "Draft article", "section_id": cls.section.id,
            "body": "<p>not ready</p>", "state": "draft",
        })

    # -- reader --------------------------------------------------------
    def test_reader_can_read_a_published_article(self):
        article = self.published.with_user(self.reader)
        self.assertEqual(article.name, "Published article")

    def test_reader_cannot_edit_an_article(self):
        with self.assertRaises(AccessError):
            self.published.with_user(self.reader).write({"name": "Vandalised"})

    def test_reader_cannot_create_an_article(self):
        with self.assertRaises(AccessError):
            self.Article.with_user(self.reader).create({"name": "Sneaky"})

    def test_reader_cannot_delete_an_article(self):
        with self.assertRaises(AccessError):
            self.published.with_user(self.reader).unlink()

    def test_drafts_are_hidden_from_readers(self):
        visible = self.Article.with_user(self.reader).search([])
        self.assertIn(self.published, visible)
        self.assertNotIn(self.draft, visible)

    def test_reading_a_draft_directly_is_refused(self):
        with self.assertRaises(AccessError):
            self.draft.with_user(self.reader).read(["name"])

    def test_reader_cannot_edit_sections_or_tags(self):
        with self.assertRaises(AccessError):
            self.section.with_user(self.reader).write({"name": "Renamed"})
        with self.assertRaises(AccessError):
            self.env["drkds.lite.kb.tag"].with_user(self.reader).create({"name": "nope"})

    def test_reader_may_still_bookmark(self):
        """A bookmark must not require write access to the article."""
        article = self.published.with_user(self.reader)
        article.action_toggle_favourite()
        article.invalidate_recordset()
        self.assertTrue(article.is_favourite)

    def test_bookmarks_of_others_are_not_visible(self):
        self.published.with_user(self.reader).action_toggle_favourite()
        others = self.env["drkds.kb.favourite"].with_user(self.editor).search([])
        self.assertFalse(others.filtered(lambda f: f.user_id == self.reader))

    # -- editor --------------------------------------------------------
    def test_editor_sees_drafts_and_can_write(self):
        visible = self.Article.with_user(self.editor).search([])
        self.assertIn(self.draft, visible)
        self.draft.with_user(self.editor).write({"name": "Draft article, revised"})
        self.assertEqual(self.draft.name, "Draft article, revised")

    def test_editor_can_create_and_publish(self):
        article = self.Article.with_user(self.editor).create({"name": "Fresh"})
        article.action_publish()
        self.assertEqual(article.state, "published")
        self.assertIn(article, self.Article.with_user(self.reader).search([]))

    def test_editor_manages_sections(self):
        child = self.env["drkds.lite.kb.section"].with_user(self.editor).create({
            "name": "Leave", "parent_id": self.section.id,
        })
        self.assertEqual(child.complete_name, "Handbook / Leave")
