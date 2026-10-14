# Part of the drkds free suite for Odoo 19 Community. See LICENSE (LGPL-3).
"""The wizard as the web client drives it.

The web client loads a form's arch and field descriptions with ``get_views``
and a context stripped down to ``lang`` and the ``*_view_ref`` keys
(``web/static/src/views/view_service.js``). It then reads the record,
searches a picker with ``web_name_search`` and the field's domain evaluated
on the record, saves with ``web_save`` and calls the buttons.

These tests make the same calls with the same context. The first version of
this wizard offered its fields through a Selection computed from a context
key: every Python call that passed the key saw a full list, and the browser,
which never sends it, showed an empty "Field to Update" dropdown.
"""
from lxml import etree

from odoo.tests import tagged
from odoo.tools.safe_eval import safe_eval

from .common import MassUpdateCommon

WIZARD = "drkds.mass.update.wizard"


@tagged("post_install", "-at_install")
class TestInTheWebClient(MassUpdateCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.line = cls._enable("res.partner")
        cls.salesperson = cls.env["res.users"].create({
            "name": "Aakash Vora", "login": "drkds_mup_aakash",
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
        })
        cls.dealers = cls.Partner.create([
            {"name": "Shree Hari Pumps"},
            {"name": "Patel Irrigation Centre"},
            {"name": "Gayatri Traders"},
        ])

    def _client(self, model_or_records):
        """As the clerk's browser calls it: the clerk's uid and a context
        holding the language only."""
        return model_or_records.with_user(self.clerk).with_context({"lang": "en_US"})

    def _open(self):
        """Actions > Mass update on the dealers: the action the browser gets
        back from the bound server action."""
        action = self.line.server_action_id.with_user(self.clerk).with_context(
            lang="en_US", active_model="res.partner", active_ids=self.dealers.ids,
        ).run()
        self.assertEqual(action["res_model"], WIZARD)
        self.assertTrue(action.get("res_id"), "the dialog opens an existing wizard")
        return self._client(self.Wizard).browse(action["res_id"])

    def _load_form(self):
        """``get_views`` as view_service.js sends it."""
        views = self._client(self.Wizard).get_views([(False, "form")])
        return etree.fromstring(views["views"]["form"]["arch"]), views["models"][WIZARD]["fields"]

    def _offered(self, wizard, field_name, name=""):
        """``[(id, label)]`` the picker of ``field_name`` offers on the opened
        wizard when the user types ``name``: the field's domain evaluated on
        the record, then ``web_name_search`` as the user."""
        arch, fields_desc = self._load_form()
        nodes = arch.xpath("//field[@name='%s']" % field_name)
        self.assertEqual(len(nodes), 1, "%s is in the form" % field_name)
        desc = fields_desc[field_name]
        self.assertEqual(desc["type"], "many2one", "%s is a record picker" % field_name)
        domain = nodes[0].get("domain") or desc.get("domain") or []
        if isinstance(domain, str):
            domain = safe_eval(domain, {"id": wizard.id})
        found = self._client(self.env[desc["relation"]]).web_name_search(
            name, {"display_name": {}}, domain=domain, limit=500
        )
        return [(row["id"], row["display_name"]) for row in found]

    def test_no_selection_in_the_form_depends_on_the_context(self):
        # Whatever a selection of this form offers, it offers in the browser.
        _arch, fields_desc = self._load_form()
        for name, desc in fields_desc.items():
            if desc["type"] == "selection":
                self.assertTrue(desc["selection"], "%s has no options in the browser" % name)

    def test_a_salesperson_is_set_through_the_browser_calls(self):
        wizard = self._open()
        # Field step: the picker offers every field the clerk may update.
        offered = self._offered(wizard, "field_choice_id")
        self.assertEqual(
            [label for _id, label in offered],
            [label for _name, label in
             self.Wizard.with_user(self.clerk)._get_writable_fields("res.partner")],
        )
        self.assertGreater(len(offered), 20)
        self.assertIn("Salesperson", [label for _id, label in offered])
        typed = self._offered(wizard, "field_choice_id", "Salesperson")
        self.assertEqual([label for _id, label in typed], ["Salesperson"])

        # Pick it and press Next, as the dialog does.
        wizard.web_save({"field_choice_id": typed[0][0]}, {"field_label": {}})
        self.assertEqual(wizard.action_next()["res_id"], wizard.id)
        _arch, fields_desc = self._load_form()
        data = wizard.web_read({
            "state": {}, "field_label": {}, "field_type": {}, "relation_model": {},
            "field_choice_id": {"fields": {"display_name": {}}},
        })[0]
        self.assertEqual(data["state"], "value")
        self.assertEqual(data["field_label"], "Salesperson")
        self.assertEqual(data["field_type"], "many2one")
        self.assertEqual(data["field_choice_id"]["display_name"], "Salesperson")
        # Value step: the record picker takes its model from a field of the
        # record, not from the context.
        self.assertEqual(fields_desc["value_record_id"]["type"], "many2one_reference")
        self.assertEqual(fields_desc["value_record_id"]["model_field"], "relation_model")
        self.assertEqual(data["relation_model"], "res.users")
        users = self._client(self.env[data["relation_model"]]).web_name_search(
            "Aakash", {"display_name": {}}
        )
        self.assertIn(self.salesperson.id, [row["id"] for row in users])

        # Apply.
        wizard.web_save({"value_record_id": self.salesperson.id}, {})
        wizard.action_apply()
        data = wizard.web_read({"state": {}, "updated_count": {}, "failed_count": {}})[0]
        self.assertEqual(
            (data["state"], data["updated_count"], data["failed_count"]), ("done", 3, 0)
        )
        self.assertEqual(self.dealers.user_id, self.salesperson)

    def test_a_selection_value_is_picked_through_the_browser_calls(self):
        wizard = self._open()
        address_type = [
            choice for choice in self._offered(wizard, "field_choice_id", "Address Type")
            if choice[1] == "Address Type"
        ]
        self.assertEqual(len(address_type), 1)
        wizard.web_save({"field_choice_id": address_type[0][0]}, {})
        wizard.action_next()
        # The choice picker offers the field's own choices, labels included.
        offered = self._offered(wizard, "value_choice_id")
        expected = self.Partner.fields_get(["type"], ["selection"])["type"]["selection"]
        self.assertEqual([label for _id, label in offered], [label for _key, label in expected])
        delivery = [choice for choice in offered if choice[1] == "Delivery"]
        self.assertEqual(len(delivery), 1)
        wizard.web_save({"value_choice_id": delivery[0][0]}, {})
        wizard.action_apply()
        self.assertEqual(self.dealers.mapped("type"), ["delivery"] * 3)
        self.assertEqual(wizard.updated_count, 3)
        # Another user's browser finds nothing in that wizard's pickers.
        spy = self.Choice.with_user(self.reader).with_context({"lang": "en_US"})
        domain = [("wizard_id", "=", wizard.id)]
        self.assertFalse(spy.web_name_search("", {"display_name": {}}, domain=domain))
