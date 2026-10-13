# Part of the drkds free suite for Odoo 19 Community. See LICENSE (LGPL-3).
"""Unit tests: which fields are offered, each value type, access errors
reported rather than raised, and the bound action's life cycle."""
import datetime

from psycopg2 import IntegrityError

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.drkds_mass_update import uninstall_hook

from .common import CTX_FIELD, CTX_MODEL, MassUpdateCommon


@tagged("post_install", "-at_install")
class TestFieldList(MassUpdateCommon):
    def test_offered_and_excluded_fields_on_partner(self):
        names = self.Wizard.with_user(self.clerk)._get_writable_field_names("res.partner")
        # Offered: stored, writable, of a supported type.
        for name in ("name", "ref", "comment", "active", "color", "type",
                     "parent_id", "category_id", "user_id", "partner_latitude",
                     "website"):
            self.assertIn(name, names, name)
        # Excluded, with the reason each one stands for.
        self.assertNotIn("id", names)
        self.assertNotIn("create_uid", names)
        self.assertNotIn("create_date", names)
        self.assertNotIn("write_uid", names)
        self.assertNotIn("write_date", names)
        self.assertNotIn("image_1920", names, "binary")
        self.assertNotIn("display_name", names, "computed, not stored")
        self.assertNotIn("commercial_partner_id", names, "computed stored, no inverse")
        self.assertNotIn("complete_name", names, "computed stored, no inverse")
        self.assertNotIn("child_ids", names, "one2many")
        self.assertNotIn("user_ids", names, "one2many")
        self.assertNotIn("tz_offset", names, "not stored")

    def test_field_selection_follows_the_model_in_context(self):
        options = self.Wizard.with_user(self.clerk).with_context(
            **{CTX_MODEL: "res.partner"}
        )._selection_field_name()
        names = [name for name, _label in options]
        self.assertEqual(
            names, self.Wizard.with_user(self.clerk)._get_writable_field_names("res.partner")
        )
        labels = [label for _name, label in options]
        self.assertEqual(labels, sorted(labels, key=str.lower), "sorted by label")
        self.assertIn(("ref", "Reference"), options)
        self.assertIn(("category_id", "Tags"), options)
        # No model in context, no options; an unknown model, no options.
        self.assertEqual(self.Wizard.with_user(self.clerk)._selection_field_name(), [])
        self.assertEqual(
            self.Wizard.with_context(**{CTX_MODEL: "no.such.model"})._selection_field_name(), []
        )

    def test_choice_selection_follows_the_field_in_context(self):
        options = self.Wizard.with_user(self.clerk).with_context(
            **{CTX_MODEL: "res.partner", CTX_FIELD: "type"}
        )._selection_value_selection()
        self.assertIn(("delivery", "Delivery"), options)
        self.assertEqual(
            self.Wizard.with_context(**{CTX_MODEL: "res.partner", CTX_FIELD: "ref"})
            ._selection_value_selection(),
            [],
            "a non-selection field has no choices",
        )
        self.assertEqual(self.Wizard._selection_value_selection(), [])

    def test_wizard_opens_for_a_plain_user_without_ir_model_access(self):
        # The clerk cannot read ir.model.fields, and must not need to.
        with self.assertRaises(AccessError):
            self.env["ir.model.fields"].with_user(self.clerk).search([], limit=1)
        wizard = self._wizard(self.clerk, self.Partner.create({"name": "Plain"}), "ref")
        self.assertEqual(wizard.model_description, "Contact")
        self.assertEqual(wizard.field_label, "Reference")
        self.assertEqual(wizard.field_type, "char")
        self.assertEqual(wizard.record_count, 1)
        wizard = self._step_to_value(wizard)
        self.assertEqual(wizard.state, "value")

    def test_field_restricted_to_a_missing_group_is_not_offered(self):
        # ir.mail_server.smtp_pass carries groups="base.group_system": a
        # plain user is not offered it, an administrator is.
        clerk_names = self.Wizard.with_user(self.clerk)._get_writable_field_names("ir.mail_server")
        admin_names = self.Wizard.with_user(self.admin)._get_writable_field_names("ir.mail_server")
        self.assertNotIn("smtp_pass", clerk_names)
        self.assertIn("smtp_pass", admin_names)
        self.assertIn("smtp_host", clerk_names)

    def test_a_field_outside_the_list_is_refused(self):
        partner = self.Partner.create({"name": "Refused Field"})
        wizard = self._wizard(self.clerk, partner)
        # Bypass the selection's own validation, as a crafted RPC call would.
        self.env.cr.execute(
            "UPDATE drkds_mass_update_wizard SET field_name = 'display_name' WHERE id = %s",
            [wizard.id],
        )
        wizard.invalidate_recordset()
        with self.assertRaises(UserError):
            wizard.action_next()
        with self.assertRaises(UserError):
            wizard.action_apply()

    def test_no_field_chosen_is_refused(self):
        partner = self.Partner.create({"name": "No Field"})
        wizard = self._wizard(self.clerk, partner)
        with self.assertRaises(UserError):
            wizard.action_next()
        with self.assertRaises(UserError):
            wizard.action_apply()


@tagged("post_install", "-at_install")
class TestValueTypes(MassUpdateCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partners = cls.Partner.create([
            {"name": "Asha Traders", "ref": "A1", "color": 3},
            {"name": "Bharat Mills", "ref": "B2", "color": 5},
            {"name": "Chitra Stores", "ref": "C3", "color": 7},
        ])

    def test_char(self):
        wizard = self._apply(self.clerk, self.partners, "ref", value_char="BULK")
        self.assertEqual(self.partners.mapped("ref"), ["BULK"] * 3)
        self.assertEqual(wizard.state, "done")
        self.assertEqual(wizard.updated_count, 3)
        self.assertEqual(wizard.failed_count, 0)
        self.assertEqual(wizard.record_count, 3)

    def test_char_without_value_needs_set_empty(self):
        wizard = self._step_to_value(self._wizard(self.clerk, self.partners, "ref"))
        with self.assertRaises(UserError):
            wizard.action_apply()
        self.assertEqual(self.partners.mapped("ref"), ["A1", "B2", "C3"])

    def test_text(self):
        groups = self.env["res.groups"].create([
            {"name": "drkds T1"}, {"name": "drkds T2"},
        ])
        self._apply(self.admin, groups, "comment", value_text="Line one\nLine two")
        self.assertEqual(groups.mapped("comment"), ["Line one\nLine two"] * 2)

    def test_html(self):
        self._apply(self.clerk, self.partners, "comment", value_html="<p>Call before noon</p>")
        for partner in self.partners:
            self.assertIn("Call before noon", partner.comment)

    def test_integer(self):
        self._apply(self.clerk, self.partners, "color", value_integer=9)
        self.assertEqual(self.partners.mapped("color"), [9, 9, 9])

    def test_float(self):
        self._apply(self.clerk, self.partners, "partner_latitude", value_float=19.076)
        for partner in self.partners:
            self.assertAlmostEqual(partner.partner_latitude, 19.076, places=5)

    def test_boolean(self):
        self.assertEqual(self.partners.mapped("is_company"), [False] * 3)
        self._apply(self.clerk, self.partners, "is_company", value_boolean=True)
        self.assertEqual(self.partners.mapped("is_company"), [True] * 3)

    def test_date(self):
        currency = self.env["res.currency"].create({"name": "DMU", "symbol": "D"})
        rates = self.env["res.currency.rate"].create([
            {"currency_id": currency.id, "name": "2026-01-01", "rate": 1.1},
            {"currency_id": currency.id, "name": "2026-02-01", "rate": 1.2},
        ])
        # Two rates of one currency cannot share a date, so update one.
        self._apply(self.admin, rates[1], "name", value_date=datetime.date(2026, 3, 15))
        self.assertEqual(rates[1].name, datetime.date(2026, 3, 15))
        self.assertEqual(rates[0].name, datetime.date(2026, 1, 1))

    def test_datetime(self):
        cron_model = self.env["ir.model"]._get("drkds.mass.update.model")
        crons = self.env["ir.cron"].create([
            {"name": "drkds mup cron %d" % i, "model_id": cron_model.id,
             "state": "code", "code": "True", "interval_number": 1,
             "interval_type": "days", "active": False}
            for i in range(2)
        ])
        when = datetime.datetime(2026, 12, 31, 18, 30, 0)
        self._apply(self.admin, crons, "nextcall", value_datetime=when)
        self.assertEqual(crons.mapped("nextcall"), [when, when])

    def test_selection(self):
        self._apply(self.clerk, self.partners, "type", value_selection="delivery")
        self.assertEqual(self.partners.mapped("type"), ["delivery"] * 3)

    def test_selection_needs_a_choice(self):
        wizard = self._step_to_value(self._wizard(self.clerk, self.partners, "type"))
        with self.assertRaises(UserError):
            wizard.action_apply()

    def test_many2one(self):
        parent = self.Partner.create({"name": "Head Office", "is_company": True})
        self._apply(self.clerk, self.partners, "parent_id", value_record_id=parent.id)
        self.assertEqual(self.partners.mapped("parent_id"), parent)

    def test_many2one_to_a_missing_record_is_refused(self):
        wizard = self._step_to_value(self._wizard(self.clerk, self.partners, "parent_id"))
        wizard.value_record_id = 99999999
        with self.assertRaises(UserError):
            wizard.action_apply()

    def test_many2many_adds_without_removing(self):
        Tag = self.env["res.partner.category"]
        old = Tag.create({"name": "Old Tag"})
        new = Tag.create({"name": "New Tag"})
        self.partners[0].category_id = old
        self._apply(self.clerk, self.partners, "category_id", value_record_id=new.id)
        self.assertEqual(self.partners[0].category_id, old | new)
        self.assertEqual(self.partners[1].category_id, new)
        self.assertEqual(self.partners[2].category_id, new)

    def test_set_empty_char(self):
        self._apply(self.clerk, self.partners, "ref", set_empty=True)
        self.assertEqual(self.partners.mapped("ref"), [False] * 3)

    def test_set_empty_integer_is_zero(self):
        self._apply(self.clerk, self.partners, "color", set_empty=True)
        self.assertEqual(self.partners.mapped("color"), [0, 0, 0])

    def test_set_empty_many2one(self):
        parent = self.Partner.create({"name": "Parent Co", "is_company": True})
        self.partners.write({"parent_id": parent.id})
        self._apply(self.clerk, self.partners, "parent_id", set_empty=True)
        self.assertFalse(self.partners.mapped("parent_id"))

    def test_set_empty_many2many_clears_all_tags(self):
        tag = self.env["res.partner.category"].create({"name": "Gone Tag"})
        self.partners.write({"category_id": [(4, tag.id)]})
        self._apply(self.clerk, self.partners, "category_id", set_empty=True)
        self.assertFalse(self.partners.mapped("category_id"))

    def test_only_the_chosen_field_changes(self):
        before = self.partners.read(["name", "color", "comment", "type"])
        self._apply(self.clerk, self.partners, "ref", value_char="X")
        self.assertEqual(self.partners.read(["name", "color", "comment", "type"]), before)


@tagged("post_install", "-at_install")
class TestAccess(MassUpdateCommon):
    def test_refused_record_is_reported_not_raised(self):
        partners = self.Partner.create([
            {"name": "Open One", "ref": "O1"},
            {"name": "Locked Contact", "ref": "LOCKED"},
            {"name": "Open Two", "ref": "O2"},
        ])
        # The clerk really cannot write the locked one.
        with self.assertRaises(AccessError):
            partners[1].with_user(self.clerk).write({"color": 1})
        wizard = self._apply(self.clerk, partners, "color", value_integer=4)
        self.assertEqual(wizard.state, "done")
        self.assertEqual(wizard.updated_count, 2)
        self.assertEqual(wizard.failed_count, 1)
        self.assertEqual(partners.mapped("color"), [4, 0, 4])
        self.assertIn("Locked Contact", wizard.result_summary)
        self.assertIn("id %d" % partners[1].id, wizard.result_summary)
        self.assertNotIn("Open One", wizard.result_summary)

    def test_refused_record_in_each_batch_of_five_hundred(self):
        # 502 records: a full batch and a 2-record tail, one locked in each.
        vals = [{"name": "Batch %03d" % i, "ref": "B%03d" % i} for i in range(502)]
        vals[250]["ref"] = "LOCKED"
        vals[501]["ref"] = "LOCKED"
        partners = self.Partner.create(vals)
        wizard = self._apply(self.clerk, partners, "color", value_integer=2)
        self.assertEqual(wizard.updated_count, 500)
        self.assertEqual(wizard.failed_count, 2)
        colors = partners.mapped("color")
        self.assertEqual(colors[250], 0)
        self.assertEqual(colors[501], 0)
        self.assertEqual(colors.count(2), 500)

    def test_user_without_write_access_on_the_model_is_refused(self):
        partner = self.Partner.create({"name": "Read Only"})
        wizard = self._step_to_value(self._wizard(self.reader, partner, "ref"))
        wizard.value_char = "X"
        with self.assertRaises(AccessError):
            wizard.action_apply()
        self.assertFalse(partner.ref)

    def test_the_write_runs_as_the_user_not_as_superuser(self):
        partner = self.Partner.create({"name": "Audit Me"})
        self._apply(self.clerk, partner, "ref", value_char="AUD")
        self.assertEqual(partner.write_uid, self.clerk)

    def test_non_administrator_cannot_enable_models(self):
        with self.assertRaises(AccessError):
            self.Enabled.with_user(self.clerk).create({"model_id": self.partner_model.id})


@tagged("post_install", "-at_install")
class TestEnableDisable(MassUpdateCommon):
    def _bound_action_names(self, model_name):
        self.env.registry.clear_cache()
        bindings = self.env["ir.actions.actions"].get_bindings(model_name)
        return [a["name"] for a in bindings.get("action", [])]

    def test_enable_creates_a_bound_action_and_disable_removes_it(self):
        self.assertNotIn("Mass update", self._bound_action_names("res.partner"))
        line = self.Enabled.with_user(self.admin).create({"model_id": self.partner_model.id})
        action = line.server_action_id
        self.assertTrue(action)
        self.assertEqual(action.binding_model_id, self.partner_model)
        self.assertEqual(action.binding_type, "action")
        self.assertEqual(action.model_id, self.partner_model)
        self.assertEqual(action.state, "code")
        self.assertEqual(action.group_ids, self.env.ref("base.group_user"))
        self.assertIn("Mass update", self._bound_action_names("res.partner"))

        line.action_disable()
        self.assertFalse(line.enabled)
        self.assertFalse(line.server_action_id)
        self.assertFalse(action.exists())
        self.assertNotIn("Mass update", self._bound_action_names("res.partner"))

        line.action_enable()
        self.assertTrue(line.server_action_id)
        self.assertIn("Mass update", self._bound_action_names("res.partner"))

    def test_deleting_the_line_removes_the_action(self):
        line = self.Enabled.with_user(self.admin).create({"model_id": self.partner_model.id})
        action = line.server_action_id
        line.unlink()
        self.assertFalse(action.exists())
        self.assertNotIn("Mass update", self._bound_action_names("res.partner"))

    def test_a_model_can_only_be_listed_once(self):
        self.Enabled.with_user(self.admin).create({"model_id": self.partner_model.id})
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            self.Enabled.with_user(self.admin).create({"model_id": self.partner_model.id})

    def test_a_wizard_model_cannot_be_enabled(self):
        wizard_model = self.env["ir.model"]._get("drkds.mass.update.wizard")
        with self.assertRaises(ValidationError):
            self.Enabled.with_user(self.admin).create({"model_id": wizard_model.id})

    def test_running_the_action_opens_the_wizard_on_the_selection(self):
        line = self.Enabled.with_user(self.admin).create({"model_id": self.partner_model.id})
        partners = self.Partner.create([{"name": "Run A"}, {"name": "Run B"}])
        result = line.server_action_id.with_user(self.clerk).with_context(
            active_model="res.partner", active_ids=partners.ids
        ).run()
        self.assertEqual(result["res_model"], "drkds.mass.update.wizard")
        self.assertEqual(result["target"], "new")
        self.assertEqual(result["context"]["default_model_name"], "res.partner")
        self.assertEqual(result["context"][CTX_MODEL], "res.partner")
        self.assertEqual(
            result["context"]["default_res_ids"], ",".join(str(i) for i in partners.ids)
        )
        wizard = self.Wizard.with_user(self.clerk).with_context(**result["context"]).create({})
        self.assertEqual(wizard.record_count, 2)
        self.assertEqual(wizard._get_res_ids(), partners.ids)
        self.assertEqual(wizard.model_name, "res.partner")
        self.assertIn("ref", [n for n, _l in wizard._selection_field_name()])

    def test_uninstall_hook_removes_every_bound_action(self):
        users_model = self.env["ir.model"]._get("res.users")
        lines = self.Enabled.with_user(self.admin).create([
            {"model_id": self.partner_model.id},
            {"model_id": users_model.id},
        ])
        actions = lines.server_action_id
        self.assertEqual(len(actions), 2)
        uninstall_hook(self.env)
        self.assertFalse(actions.exists())
        self.assertFalse(lines.mapped("server_action_id"))
        self.assertNotIn("Mass update", self._bound_action_names("res.partner"))
        self.assertNotIn("Mass update", self._bound_action_names("res.users"))
