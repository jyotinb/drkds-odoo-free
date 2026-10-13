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
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_line = cls._enable("res.partner")

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
        cls._enable("res.partner")
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
        self._enable("res.groups")
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
        self._enable("res.currency.rate")
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
        self._enable("ir.cron")
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

    def test_a_choice_outside_the_field_selection_is_refused(self):
        # res.partner.lang takes its choices from a method, and the ORM does
        # not validate such a selection: any string would be stored. The
        # wizard's own choice field is method-based too, so a crafted call
        # can send anything; the wizard must check it against the field.
        self.partners.write({"lang": False})
        wizard = self._step_to_value(self._wizard(self.clerk, self.partners, "lang"))
        wizard.value_selection = "xx_XX"
        with self.assertRaises(UserError):
            wizard.action_apply()
        self.assertEqual(self.partners.mapped("lang"), [False] * 3)
        wizard.value_selection = "en_US"
        wizard.action_apply()
        self.assertEqual(self.partners.mapped("lang"), ["en_US"] * 3)

    def test_set_empty_is_refused_on_a_required_field(self):
        # Emptying a required field used to reach the database and fail
        # there with a NOT NULL violation.
        self._enable("res.partner.category")
        tags = self.env["res.partner.category"].create([{"name": "Keep A"}, {"name": "Keep B"}])
        self.assertTrue(tags._fields["name"].required)
        wizard = self._step_to_value(self._wizard(self.clerk, tags, "name"))
        self.assertTrue(wizard.field_required)
        wizard.set_empty = True
        with self.assertRaises(UserError):
            wizard.action_apply()
        self.assertEqual(tags.mapped("name"), ["Keep A", "Keep B"])
        # A required number may still be set to zero.
        wizard = self._step_to_value(self._wizard(self.clerk, tags, "color"))
        wizard.set_empty = True
        wizard.action_apply()
        self.assertEqual(tags.mapped("color"), [0, 0])

    def test_a_value_record_the_user_cannot_read_is_refused(self):
        # A partner of another company is invisible to the clerk, so the
        # picker never offers it; a crafted id must not get through either.
        other_company = self.env["res.company"].create({"name": "drkds Other Co"})
        foreign = self.Partner.create(
            {"name": "Foreign Parent", "company_id": other_company.id, "is_company": True}
        )
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            foreign.with_user(self.clerk).read(["name"])
        wizard = self._step_to_value(self._wizard(self.clerk, self.partners, "parent_id"))
        wizard.value_record_id = foreign.id
        with self.assertRaises(AccessError):
            wizard.action_apply()
        self.assertFalse(self.partners.parent_id)
        self.assertEqual(wizard.state, "value", "nothing was applied")


@tagged("post_install", "-at_install")
class TestAccess(MassUpdateCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_line = cls._enable("res.partner")

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

    def test_another_user_cannot_read_or_change_my_wizard(self):
        # The administrator is at the value step on one contact. A plain
        # user who could rewrite that wizard would point it at res.users and
        # let the administrator's Apply put them in the Settings group.
        partner = self.Partner.create({"name": "Admin Target"})
        wizard = self._step_to_value(self._wizard(self.admin, partner, "ref"))
        system = self.env.ref("base.group_system")
        self.env.invalidate_all()
        spy = self.Wizard.with_user(self.reader)
        self.assertFalse(spy.search([("id", "=", wizard.id)]))
        with self.assertRaises(AccessError):
            spy.browse(wizard.id).read(["model_name", "res_ids"])
        with self.assertRaises(AccessError):
            spy.with_context(**{CTX_MODEL: "res.users"}).browse(wizard.id).write({
                "model_name": "res.users",
                "res_ids": str(self.reader.id),
                "field_name": "group_ids",
                "value_record_id": system.id,
            })
        with self.assertRaises(AccessError):
            spy.browse(wizard.id).unlink()
        wizard.value_char = "ADM"
        wizard.action_apply()
        self.assertEqual(wizard.model_name, "res.partner")
        self.assertEqual(partner.ref, "ADM")
        self.env.invalidate_all()
        self.assertNotIn(system, self.reader.group_ids)

    def test_a_model_that_is_not_enabled_is_refused(self):
        partner = self.Partner.create({"name": "Not Enabled", "ref": "NE"})
        wizard = self._wizard(self.clerk, partner, "ref")
        self.partner_line.action_disable()
        with self.assertRaises(UserError) as caught:
            wizard.action_next()
        self.assertNotIsInstance(caught.exception, AccessError)
        self.assertIn("not enabled", caught.exception.args[0])
        # A wizard crafted directly on a model nobody enabled, by a user who
        # may write that model, is refused as well.
        group = self.env["res.groups"].create({"name": "drkds Not Enabled"})
        crafted = self.Wizard.with_user(self.admin).with_context(**{CTX_MODEL: "res.groups"}).create({
            "model_name": "res.groups",
            "res_ids": str(group.id),
            "field_name": "comment",
            "state": "value",
            "value_text": "crafted",
        })
        with self.assertRaises(UserError) as caught:
            crafted.with_context(**{CTX_FIELD: "comment"}).action_apply()
        self.assertIn("not enabled", caught.exception.args[0])
        self.assertFalse(group.comment)
        self.assertEqual(partner.ref, "NE")

    def test_an_unreadable_record_is_reported_by_id_only(self):
        # Hidden from the clerk for reading and writing: reported, counted,
        # and its name is not disclosed in the result.
        hidden_group = self.env["res.groups"].create({"name": "drkds Hidden Contacts"})
        self.clerk.write({"group_ids": [(4, hidden_group.id)]})
        self.env["ir.rule"].create({
            "name": "drkds test: contacts marked HIDDEN are invisible",
            "model_id": self.partner_model.id,
            "domain_force": "[('ref', '!=', 'HIDDEN')]",
            "groups": [(4, hidden_group.id)],
            "perm_read": True, "perm_write": True,
            "perm_create": False, "perm_unlink": False,
        })
        partners = self.Partner.create([
            {"name": "Seen One"},
            {"name": "Secret Holdings", "ref": "HIDDEN"},
        ])
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            partners[1].with_user(self.clerk).read(["name"])
        wizard = self._apply(self.clerk, partners, "color", value_integer=8)
        self.assertEqual(wizard.updated_count, 1)
        self.assertEqual(wizard.failed_count, 1)
        self.assertIn("<strong>#%d</strong>" % partners[1].id, wizard.result_summary)
        self.assertNotIn("Secret Holdings", wizard.result_summary)
        self.assertEqual(partners.mapped("color"), [8, 0])

    def test_a_record_deleted_after_selection_is_reported(self):
        partners = self.Partner.create([{"name": "Keep 1"}, {"name": "Gone"}, {"name": "Keep 2"}])
        gone_id = partners[1].id
        wizard = self._step_to_value(self._wizard(self.clerk, partners, "ref"))
        wizard.value_char = "K"
        partners[1].unlink()
        wizard.action_apply()
        self.assertEqual(wizard.record_count, 3)
        self.assertEqual(wizard.updated_count, 2)
        self.assertEqual(wizard.failed_count, 1)
        self.assertIn("(id %d)" % gone_id, wizard.result_summary)
        self.assertIn("no longer exists", wizard.result_summary)
        self.assertEqual((partners[0] | partners[2]).mapped("ref"), ["K", "K"])

    def test_a_repeated_id_counts_once(self):
        partners = self.Partner.create([{"name": "Twice"}, {"name": "Once"}])
        wizard = self.Wizard.with_user(self.clerk).with_context(**{
            CTX_MODEL: "res.partner",
            "active_model": "res.partner",
            "active_ids": [partners[0].id, partners[0].id, partners[1].id],
        }).create({"field_name": "color"})
        self.assertEqual(wizard.record_count, 2)
        wizard = self._step_to_value(wizard)
        wizard.value_integer = 6
        wizard.action_apply()
        self.assertEqual(wizard.updated_count, 2)
        self.assertEqual(partners.mapped("color"), [6, 6])

    def test_the_result_is_safe_html(self):
        # A record name is escaped in the result list...
        partners = self.Partner.create([
            {"name": "Plain"},
            {"name": "<img src=x onerror=alert(1)>", "ref": "LOCKED"},
        ])
        wizard = self._apply(self.clerk, partners, "color", value_integer=1)
        self.assertEqual(wizard.failed_count, 1)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", wizard.result_summary)
        self.assertNotIn("<img", wizard.result_summary)
        # ...and the result field cannot hold live markup written over RPC.
        crafted = self.Wizard.with_user(self.clerk).create({
            "model_name": "res.partner",
            "result_summary": '<img src="x" onerror="alert(2)"><script>alert(3)</script>',
        })
        self.assertNotIn("onerror", crafted.result_summary)
        self.assertNotIn("<script", crafted.result_summary)


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

    def test_abstract_and_sql_view_models_cannot_be_enabled(self):
        # image.mixin has no table; res.device is a database view. Either
        # would carry a Mass update entry that can never write anything.
        for model_name in ("image.mixin", "res.device"):
            with self.subTest(model=model_name), self.assertRaises(ValidationError):
                self.Enabled.with_user(self.admin).create(
                    {"model_id": self.env["ir.model"]._get(model_name).id}
                )

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

    def test_uninstall_hook_removes_renamed_and_copied_actions(self):
        line = self.Enabled.with_user(self.admin).create({"model_id": self.partner_model.id})
        renamed = line.server_action_id
        renamed.name = "Bulk edit"
        # Duplicate on the server action form: a copy no line knows about,
        # still opening the wizard that uninstalling removes.
        copied = renamed.copy({"name": "Mass update (copy)"})
        uninstall_hook(self.env)
        self.assertFalse(renamed.exists())
        self.assertFalse(copied.exists())
        self.assertEqual(self._bound_action_names("res.partner").count("Mass update (copy)"), 0)
