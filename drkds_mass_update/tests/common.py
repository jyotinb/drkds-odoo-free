# Part of the drkds free suite for Odoo 19 Community. See LICENSE (LGPL-3).
"""Shared fixtures: an administrator who enables models, a clerk who may edit
contacts but is locked out of one of them by a record rule, and a helper
that drives the wizard the way the form does."""
from odoo.tests import TransactionCase, new_test_user

from odoo.addons.drkds_mass_update.wizard.drkds_mass_update_wizard import (
    CTX_FIELD,
    CTX_MODEL,
)


class MassUpdateCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Wizard = cls.env["drkds.mass.update.wizard"]
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

    def _wizard(self, user, records, field_name=None):
        """Create the wizard as ``user`` on ``records``, as the bound action
        does: the model travels in the context, the ids in the defaults."""
        ctx = {
            "active_model": records._name,
            "active_ids": records.ids,
            CTX_MODEL: records._name,
        }
        vals = {}
        if field_name:
            vals["field_name"] = field_name
        return self.Wizard.with_user(user).with_context(**ctx).create(vals)

    def _step_to_value(self, wizard):
        """Press Next and come back with the context the re-opened dialog
        carries, exactly as the client would."""
        result = wizard.action_next()
        self.assertEqual(result["res_id"], wizard.id)
        return wizard.with_context(**result["context"])

    def _apply(self, user, records, field_name, **values):
        wizard = self._step_to_value(self._wizard(user, records, field_name))
        if values:
            wizard.write(values)
        wizard.action_apply()
        return wizard
