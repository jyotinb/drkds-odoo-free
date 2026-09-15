from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestKbSection(TransactionCase):
    """The section tree: naming, nesting and the refusal to form a loop."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Section = cls.env["drkds.kb.section"]
        cls.handbook = cls.Section.create({"name": "Handbook"})
        cls.onboarding = cls.Section.create({
            "name": "Onboarding", "parent_id": cls.handbook.id,
        })
        cls.first_week = cls.Section.create({
            "name": "First Week", "parent_id": cls.onboarding.id,
        })

    def test_complete_name_is_the_full_path(self):
        self.assertEqual(self.handbook.complete_name, "Handbook")
        self.assertEqual(self.onboarding.complete_name, "Handbook / Onboarding")
        self.assertEqual(
            self.first_week.complete_name, "Handbook / Onboarding / First Week"
        )

    def test_renaming_an_ancestor_repaths_descendants(self):
        """complete_name is recursive, so a rename must flow all the way down."""
        self.handbook.name = "Company Handbook"
        self.assertEqual(
            self.first_week.complete_name,
            "Company Handbook / Onboarding / First Week",
        )

    def test_reparenting_repaths_descendants(self):
        policies = self.Section.create({"name": "Policies"})
        self.onboarding.parent_id = policies
        self.assertEqual(
            self.first_week.complete_name, "Policies / Onboarding / First Week"
        )

    def test_parent_path_supports_child_of(self):
        """The materialised path is what makes branch queries cheap."""
        self.assertTrue(self.first_week.parent_path.startswith(self.handbook.parent_path))
        branch = self.Section.search([("id", "child_of", self.handbook.id)])
        self.assertEqual(branch, self.handbook | self.onboarding | self.first_week)

    def test_direct_cycle_is_refused(self):
        """Odoo raises on the parent_store update; the constraint is the backstop."""
        with self.assertRaises(UserError):
            self.handbook.parent_id = self.handbook

    def test_indirect_cycle_is_refused(self):
        """Handbook cannot be filed under its own grandchild."""
        with self.assertRaises(UserError):
            self.handbook.parent_id = self.first_week

    def test_article_counts_direct_and_branch(self):
        Article = self.env["drkds.kb.article"]
        Article.create({"name": "Welcome", "section_id": self.onboarding.id})
        Article.create({"name": "Day One", "section_id": self.first_week.id})
        self.assertEqual(self.onboarding.article_count, 1)
        self.assertEqual(self.onboarding.article_count_total, 2)
        self.assertEqual(self.handbook.article_count, 0)
        self.assertEqual(self.handbook.article_count_total, 2)
