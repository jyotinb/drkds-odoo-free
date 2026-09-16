from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestKbArticle(TransactionCase):
    """Article behaviour: filing, the plain text copy, search and bookmarks."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Section = cls.env["drkds.lite.kb.section"]
        cls.Article = cls.env["drkds.lite.kb.article"]
        cls.handbook = cls.Section.create({"name": "Handbook"})
        cls.leave = cls.Section.create({"name": "Leave", "parent_id": cls.handbook.id})
        cls.expenses = cls.Section.create({
            "name": "Expenses", "parent_id": cls.handbook.id,
        })
        cls.tag = cls.env["drkds.lite.kb.tag"].create({"name": "policy"})

    # -- filing --------------------------------------------------------
    def test_moving_an_article_updates_section_and_counts(self):
        article = self.Article.create({
            "name": "Claiming travel", "section_id": self.leave.id,
        })
        self.assertEqual(self.leave.article_count, 1)
        self.assertEqual(self.expenses.article_count, 0)

        article.section_id = self.expenses
        self.leave.invalidate_recordset()
        self.expenses.invalidate_recordset()
        self.assertEqual(article.section_path, "Handbook / Expenses")
        self.assertEqual(self.leave.article_count, 0)
        self.assertEqual(self.expenses.article_count, 1)
        self.assertIn(article, self.expenses.article_ids)
        self.assertNotIn(article, self.leave.article_ids)

    def test_article_is_found_under_the_parent_branch(self):
        article = self.Article.create({
            "name": "Sick leave", "section_id": self.leave.id,
        })
        found = self.Article.search([("section_id", "child_of", self.handbook.id)])
        self.assertIn(article, found)

    # -- full text -----------------------------------------------------
    def test_body_is_flattened_into_plain_text(self):
        article = self.Article.create({
            "name": "Travel", "body": "<p>Book via <strong>Zephyrine</strong> only.</p>",
        })
        self.assertIn("Zephyrine", article.body_text)
        self.assertNotIn("<strong>", article.body_text)

    def test_full_text_search_finds_a_word_only_in_the_body(self):
        """The whole point of the plain text copy."""
        article = self.Article.create({
            "name": "Travel policy",
            "body": "<p>Reimbursement requires a <em>quadrangle</em> receipt.</p>",
        })
        self.Article.create({"name": "Unrelated", "body": "<p>Nothing to see.</p>"})

        self.assertFalse(self.Article.search([("name", "ilike", "quadrangle")]))
        by_body = self.Article.search([("full_text", "ilike", "quadrangle")])
        self.assertEqual(by_body, article)

    def test_full_text_search_also_covers_title_and_tags(self):
        titled = self.Article.create({"name": "Quadrangle handbook"})
        tagged_article = self.Article.create({
            "name": "Something else", "tag_ids": [(4, self.tag.id)],
        })
        self.assertIn(titled, self.Article.search([("full_text", "ilike", "quadrangle")]))
        self.assertIn(
            tagged_article, self.Article.search([("full_text", "ilike", "policy")])
        )

    def test_full_text_negative_operator_excludes(self):
        match = self.Article.create({"name": "Q", "body": "<p>quadrangle</p>"})
        other = self.Article.create({"name": "R", "body": "<p>triangle</p>"})
        result = self.Article.search([("full_text", "not ilike", "quadrangle")])
        self.assertIn(other, result)
        self.assertNotIn(match, result)

    def test_body_text_follows_an_edit(self):
        article = self.Article.create({"name": "Draft", "body": "<p>alpha</p>"})
        article.body = "<p>beta</p>"
        self.assertNotIn("alpha", article.body_text)
        self.assertIn("beta", article.body_text)

    # -- metadata ------------------------------------------------------
    def test_publishing_stamps_a_date(self):
        article = self.Article.create({"name": "Notice"})
        self.assertEqual(article.state, "draft")
        self.assertFalse(article.published_date)
        article.action_publish()
        self.assertEqual(article.state, "published")
        self.assertTrue(article.published_date)

    def test_last_editor_is_stamped_on_a_content_change(self):
        editor = self.env["res.users"].create({
            "name": "Second Editor", "login": "kb_second_editor",
            "group_ids": [(4, self.env.ref(
                "drkds_knowledge_base_lite.group_kb_editor").id)],
        })
        article = self.Article.create({"name": "Shared"})
        self.assertEqual(article.editor_id, self.env.user)
        article.with_user(editor).write({"body": "<p>revised</p>"})
        self.assertEqual(article.editor_id, editor)

    # -- bookmarks -----------------------------------------------------
    def test_bookmark_toggles_and_is_searchable(self):
        article = self.Article.create({"name": "Worth keeping"})
        self.assertFalse(article.is_favourite)

        article.action_toggle_favourite()
        article.invalidate_recordset()
        self.assertTrue(article.is_favourite)
        self.assertEqual(article.favourite_count, 1)
        self.assertIn(article, self.Article.search([("is_favourite", "=", True)]))

        article.action_toggle_favourite()
        article.invalidate_recordset()
        self.assertFalse(article.is_favourite)
        self.assertNotIn(article, self.Article.search([("is_favourite", "=", True)]))

    def test_bookmarks_are_per_user(self):
        other = self.env["res.users"].create({
            "name": "Other Reader", "login": "kb_other_reader",
            "group_ids": [(4, self.env.ref(
                "drkds_knowledge_base_lite.group_kb_reader").id)],
        })
        article = self.Article.create({"name": "Mine only", "state": "published"})
        article.action_toggle_favourite()
        self.assertTrue(article.is_favourite)
        self.assertFalse(article.with_user(other).is_favourite)

    # -- ordering ------------------------------------------------------
    def test_default_order_is_most_recently_updated_first(self):
        old = self.Article.create({"name": "Old"})
        new = self.Article.create({"name": "New"})
        new.flush_recordset()
        ordered = self.Article.search([("id", "in", (old | new).ids)])
        self.assertEqual(ordered[0], new)
