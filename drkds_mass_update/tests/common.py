# Part of the drkds free suite for Odoo 19 Community. See LICENSE (LGPL-3).
"""Shared fixtures: an administrator who enables models, a clerk who may edit
contacts but is locked out of one of them by a record rule, and helpers
that drive the wizard the way the form does: pick a line in the field
picker, press Next, fill the value (a line of the choice picker for a
selection field), press Apply."""
from odoo.tests import TransactionCase, new_test_user


class MassUpdateCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Wizard = cls.env["drkds.mass.update.wizard"]
        cls.Choice = cls.env["drkds.mass.update.field.choice"]
        cls.Enabled = cls.env["drkds.mass.update.model"]
        cls.Partner = cls.env["res.partner"]
        cls.partner_model = cls.env["ir.model"]._get("res.partner")

        cls.admin = new_test_user(
            cls.env, login="drkds_mup_admin", name="Mass Update Admin",
            groups="base.group_user,base.group_system",
        )
        # The clerk may write contacts, except the ones a record rule locks.
        cls.locked_group = cls.env["res.groups"].create({"name": "drkds Locked Contacts"})
        cls.clerk = new_test_user(
            cls.env, login="drkds_mup_clerk", name="Mass Update Clerk",
            groups="base.group_user,base.group_partner_manager",
        )
        cls.clerk.write({"group_ids": [(4, cls.locked_group.id)]})
        cls.lock_rule = cls.env["ir.rule"].create({
            "name": "drkds test: contacts marked LOCKED cannot be written",
            "model_id": cls.partner_model.id,
            "domain_force": "[('ref', '!=', 'LOCKED')]",
            "groups": [(4, cls.locked_group.id)],
            "perm_read": False,
            "perm_write": True,
            "perm_create": False,
            "perm_unlink": False,
        })
        # Someone with no write access on contacts at all.
        cls.reader = new_test_user(
            cls.env, login="drkds_mup_reader", name="Mass Update Reader",
            groups="base.group_user",
        )

    @classmethod
    def _enable(cls, *model_names):
        """Enable mass update on these models, as the administrator does.
        The wizard refuses any model that is not enabled."""
        return cls.env["drkds.mass.update.model"].with_user(cls.admin).create(
            [{"model_id": cls.env["ir.model"]._get(name).id} for name in model_names]
        )

    def _wizard(self, user, records, field_name=None):
        """Create the wizard as ``user`` on ``records`` (the active_model /
        active_ids fallback) and, when given, pick ``field_name`` in the
        field picker."""
        wizard = self.Wizard.with_user(user).with_context(
            active_model=records._name, active_ids=records.ids,
        ).create({})
        if field_name:
            self._pick_field(wizard, field_name)
        return wizard

    def _choice(self, wizard, kind, technical_name):
        """The ``kind`` line of ``wizard`` for ``technical_name``, as the
        picker offers it (read as the wizard's user)."""
        choice = wizard._get_choices(kind).filtered(
            lambda line: line.technical_name == technical_name
        )
        self.assertEqual(len(choice), 1, "%s %s is offered" % (kind, technical_name))
        return choice

    def _pick_field(self, wizard, field_name):
        wizard.field_choice_id = self._choice(wizard, "field", field_name)
        self.assertEqual(wizard.field_name, field_name)

    def _step_to_value(self, wizard):
        """Press Next; the dialog re-opens on the same wizard."""
        result = wizard.action_next()
        self.assertEqual(result["res_id"], wizard.id)
        return wizard

    def _apply(self, user, records, field_name, value_choice=None, **values):
        """Run the whole wizard. ``value_choice`` is the key to pick in the
        choice picker of a selection field."""
        wizard = self._step_to_value(self._wizard(user, records, field_name))
        if value_choice is not None:
            values["value_choice_id"] = self._choice(wizard, "value", value_choice).id
        if values:
            wizard.write(values)
        wizard.action_apply()
        return wizard
