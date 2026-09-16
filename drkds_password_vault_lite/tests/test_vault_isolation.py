"""Tests about who can see what. A shared vault is not a vault."""
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import VaultCase

SECRET = "only mine"


@tagged("post_install", "-at_install")
class TestVaultIsolation(VaultCase):

    def test_another_user_cannot_read_the_entry(self):
        """The record rule hides the row from every other user."""
        entry = self._entry(secret=SECRET)
        as_other = entry.with_user(self.other_user)
        self.assertFalse(
            self.Entry.with_user(self.other_user).search([("id", "=", entry.id)])
        )
        with self.assertRaises(AccessError):
            as_other.read(["name", "secret_encrypted"])

    def test_the_administrator_is_not_an_exception(self):
        """No override group: admin sees its own entries and no one else's."""
        entry = self.Entry.with_user(self.other_user).create([{
            "name": "Outsider entry", "secret": SECRET,
        }])[0]
        admin = self.env.ref("base.user_admin")
        self.assertFalse(
            self.Entry.with_user(admin).search([("id", "=", entry.id)]),
            "an administrator must not see another user's vault entry",
        )

    def test_another_user_cannot_reveal_the_secret(self):
        entry = self._entry(secret=SECRET)
        with self.assertRaises(AccessError):
            entry.with_user(self.other_user)._read_secret()

    def test_another_user_cannot_open_the_reveal_wizard(self):
        entry = self._entry(secret=SECRET)
        with self.assertRaises(AccessError):
            entry.with_user(self.other_user).action_reveal_secret()

    def test_ownership_is_taken_from_the_session_not_the_payload(self):
        """Creating an entry 'for' someone else silently keeps it for yourself."""
        entry = self.Entry.with_user(self.other_user).create([{
            "name": "Planted", "user_id": self.env.user.id, "secret": SECRET,
        }])[0]
        self.assertEqual(entry.sudo().user_id, self.other_user)

    def test_ownership_cannot_be_transferred(self):
        entry = self._entry(secret=SECRET)
        with self.assertRaises(UserError):
            entry.write({"user_id": self.other_user.id})

    def test_another_user_cannot_read_the_access_log(self):
        entry = self._entry(secret=SECRET)
        entry.action_reveal_secret()
        self.assertFalse(
            self.Log.with_user(self.other_user).search([("entry_id", "=", entry.id)])
        )

    def test_folders_and_tags_are_personal_too(self):
        folder = self.env["drkds.vault.folder"].create([{"name": "Banking"}])[0]
        tag = self.env["drkds.lite.vault.tag"].create([{"name": "work"}])[0]
        self.assertFalse(
            self.env["drkds.vault.folder"].with_user(self.other_user)
            .search([("id", "=", folder.id)])
        )
        self.assertFalse(
            self.env["drkds.lite.vault.tag"].with_user(self.other_user)
            .search([("id", "=", tag.id)])
        )

    def test_no_rule_is_group_scoped(self):
        """Every vault rule is global, so no group can be granted an override."""
        rules = self.env["ir.rule"].search([
            ("model_id.model", "in", [
                "drkds.lite.vault.entry", "drkds.vault.folder",
                "drkds.lite.vault.tag", "drkds.lite.vault.access.log",
            ]),
        ])
        self.assertEqual(len(rules), 4)
        for rule in rules:
            self.assertTrue(rule['global'], rule.name)
