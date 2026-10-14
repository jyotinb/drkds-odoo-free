"""Each wizard of this module is reserved to the user who opened it.

Odoo 19 stores a wizard (transient) record like any other record: without a
rule, a user holding the model's access right could open or overwrite a
colleague's pending wizard by its id.
"""

from odoo.tests import TransactionCase, tagged
from odoo.tests.common import new_test_user

THIS_MODULE = "drkds_in_fy_sequence"
CREATOR_ONLY = "[('create_uid','=',user.id)]"


@tagged("post_install", "-at_install")
class TestWizardsStayPrivate(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wizard_names = sorted(
            name for name, model in cls.env.registry.items()
            if model._transient and model._original_module == THIS_MODULE
        )

    def test_every_wizard_has_a_creator_rule(self):
        self.assertTrue(self.wizard_names)
        for name in self.wizard_names:
            rules = self.env["ir.rule"].search([("model_id.model", "=", name), ("global", "=", True)])
            self.assertIn(CREATOR_ONLY, [rule.domain_force.replace(" ", "") for rule in rules],
                          "%s has no creator rule" % name)

    def test_rule_binds_an_ordinary_user(self):
        clerk = new_test_user(self.env, login="drkds_lite_wizard_clerk", groups="base.group_user")
        for name in self.wizard_names:
            for mode in ("read", "write", "unlink"):
                domain = self.env["ir.rule"].with_user(clerk)._compute_domain(name, mode)
                self.assertIn("create_uid", str(domain), (name, mode))
