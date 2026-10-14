# Part of the drkds free suite for Odoo 19 Community. See LICENSE (LGPL-3).
"""End to end: the administrator enables contacts, a clerk selects 200 of
them in the list, gives them a tag and then a salesperson through the bound
action and the wizard. One of the 200 is locked by a record rule, so each
run reports 199 updated and names the one it could not touch."""
from odoo.tests import tagged

from .common import MassUpdateCommon


@tagged("post_install", "-at_install")
class TestMassUpdateScenario(MassUpdateCommon):
    def test_two_hundred_contacts_get_a_tag_and_a_salesperson(self):
        # 1. The administrator enables contacts for mass update.
        line = self.Enabled.with_user(self.admin).create({"model_id": self.partner_model.id})
        self.env.registry.clear_cache()
        bindings = self.env["ir.actions.actions"].get_bindings("res.partner")
        self.assertIn("Mass update", [a["name"] for a in bindings["action"]])

        # 2. Two hundred contacts, one of them locked for the clerk.
        contacts = self.Partner.create([
            {"name": "Mailing Contact %03d" % i, "ref": "MC%03d" % i}
            for i in range(200)
        ])
        locked = contacts[77]
        locked.write({"ref": "LOCKED"})
        self.assertEqual(len(contacts), 200)
        self.assertFalse(contacts.mapped("category_id"))
        self.assertFalse(contacts.mapped("user_id"))

        tag = self.env["res.partner.category"].create({"name": "Diwali 2026 Mailing"})
        salesperson = self.env["res.users"].create({
            "name": "Priya Nair", "login": "drkds_mup_priya",
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
        })

        # 3. The clerk selects all 200 in the list and runs the bound action.
        result = line.server_action_id.with_user(self.clerk).with_context(
            active_model="res.partner", active_ids=contacts.ids
        ).run()
        self.assertEqual(result["res_model"], "drkds.mass.update.wizard")

        # 4. First pass: add the tag. The action opened the clerk's own
        #    wizard, already listing the fields the clerk may update.
        wizard = self.Wizard.with_user(self.clerk).browse(result["res_id"])
        self.assertEqual(wizard.create_uid, self.clerk)
        self.assertEqual(wizard.record_count, 200)
        self.assertEqual(wizard.model_description, "Contact")
        offered = wizard._get_choices("field").mapped("name")
        self.assertIn("Tags", offered)
        self.assertIn("Salesperson", offered)
        self._pick_field(wizard, "category_id")
        wizard = self._step_to_value(wizard)
        self.assertEqual(wizard.field_label, "Tags")
        self.assertEqual(wizard.relation_model, "res.partner.category")
        wizard.value_record_id = tag.id
        wizard.action_apply()

        self.assertEqual(wizard.state, "done")
        self.assertEqual(wizard.updated_count, 199)
        self.assertEqual(wizard.failed_count, 1)
        self.assertIn(locked.display_name, wizard.result_summary)
        tagged_contacts = contacts.filtered(lambda c: tag in c.category_id)
        self.assertEqual(len(tagged_contacts), 199)
        self.assertNotIn(locked, tagged_contacts)
        self.assertFalse(locked.category_id)
        # Written as the clerk, never as superuser: read back from the table.
        # (Checked after this first pass only. On a later pass the cached
        # write_uid already equals the clerk, so the ORM does not mark it
        # dirty, and the test harness then flushes through the test's
        # superuser environment, which stamps uid 1. Under a real request the
        # flushing environment is the user's own, so production is correct.)
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual((contacts - locked).mapped("write_uid"), self.clerk)
        self.assertEqual(locked.write_uid, self.env.user)

        # 5. Second pass, same selection: set the salesperson.
        result2 = line.server_action_id.with_user(self.clerk).with_context(
            active_model="res.partner", active_ids=contacts.ids
        ).run()
        wizard2 = self.Wizard.with_user(self.clerk).browse(result2["res_id"])
        self.assertNotEqual(wizard2, wizard, "a fresh wizard per run")
        self._pick_field(wizard2, "user_id")
        wizard2 = self._step_to_value(wizard2)
        self.assertEqual(wizard2.field_label, "Salesperson")
        wizard2.value_record_id = salesperson.id
        wizard2.action_apply()

        self.assertEqual(wizard2.updated_count, 199)
        self.assertEqual(wizard2.failed_count, 1)
        with_sales = contacts.filtered(lambda c: c.user_id == salesperson)
        self.assertEqual(len(with_sales), 199)
        self.assertFalse(locked.user_id)
        # 6. Nothing else moved on any contact.
        self.assertEqual(contacts.mapped("ref").count("LOCKED"), 1)
        self.assertEqual(
            sorted(contacts.mapped("name")),
            sorted("Mailing Contact %03d" % i for i in range(200)),
        )

        # 7. The administrator disables the model: the action is gone, the
        #    data the clerk wrote stays.
        line.action_disable()
        self.env.registry.clear_cache()
        bindings = self.env["ir.actions.actions"].get_bindings("res.partner")
        self.assertNotIn("Mass update", [a["name"] for a in bindings.get("action", [])])
        self.assertEqual(len(contacts.filtered(lambda c: tag in c.category_id)), 199)
