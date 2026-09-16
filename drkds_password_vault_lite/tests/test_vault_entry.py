"""Tests about the entry model: storage, write-only secret, access log."""
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import VaultCase

SECRET = "correct horse battery staple"


@tagged("post_install", "-at_install")
class TestVaultEntry(VaultCase):

    # -- storage -------------------------------------------------------
    def test_secret_column_holds_no_plaintext(self):
        """Read the raw column: the password is not in it, in any encoding."""
        entry = self._entry(secret=SECRET)
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT secret_encrypted FROM drkds_lite_vault_entry WHERE id = %s", (entry.id,)
        )
        stored = self.env.cr.fetchone()[0]
        self.assertTrue(stored)
        self.assertNotIn(SECRET, stored)
        self.assertNotIn(SECRET.encode().hex(), stored)
        import base64
        self.assertNotIn(base64.b64encode(SECRET.encode()).decode().rstrip("="), stored)
        self.assertTrue(stored.startswith("gAAAAA"), "expected a Fernet v1 token")

    def test_plaintext_is_in_no_column_of_the_row(self):
        """Not just the secret column: no column of the table leaks it."""
        entry = self._entry(secret=SECRET, notes="nothing sensitive here")
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT * FROM drkds_lite_vault_entry WHERE id = %s", (entry.id,)
        )
        row = self.env.cr.fetchone()
        for value in row:
            self.assertNotIn(SECRET, str(value))

    def test_secret_reads_back_empty(self):
        """The plaintext field is write-only; it never returns a value."""
        entry = self._entry(secret=SECRET)
        entry.invalidate_recordset()
        self.assertFalse(entry.secret)
        self.assertFalse(entry.read(["secret"])[0]["secret"])

    def test_secret_field_is_not_stored_searchable_or_exportable(self):
        """The ORM itself refuses to search or export the plaintext field."""
        field = self.Entry._fields["secret"]
        self.assertFalse(field.store)
        self.assertFalse(field.exportable)
        self.assertFalse(self.Entry._fields["secret_encrypted"].exportable)
        with self.assertRaises(ValueError):
            self.Entry.search([("secret", "=", SECRET)])

    def test_has_secret_flag_tracks_the_token(self):
        entry = self._entry(secret=SECRET)
        self.assertTrue(entry.has_secret)
        entry.secret = ""
        self.assertFalse(entry.secret_encrypted)
        self.assertFalse(entry.has_secret)

    def test_ordinary_write_keeps_the_secret(self):
        """Editing the title must not silently wipe the password."""
        entry = self._entry(secret=SECRET)
        token = entry.secret_encrypted
        entry.write({"name": "Renamed"})
        self.assertEqual(entry.secret_encrypted, token)
        self.assertEqual(entry._read_secret(), SECRET)

    def test_changing_the_secret_replaces_the_token(self):
        entry = self._entry(secret=SECRET)
        old = entry.secret_encrypted
        entry.write({"secret": "a different password"})
        self.assertNotEqual(entry.secret_encrypted, old)
        self.assertEqual(entry._read_secret(), "a different password")

    def test_duplicating_does_not_carry_the_password(self):
        entry = self._entry(secret=SECRET)
        copy = entry.copy()
        self.assertFalse(copy.secret_encrypted)
        self.assertFalse(copy.has_secret)

    # -- reveal and logging -------------------------------------------
    def test_reveal_returns_the_plaintext_and_logs_it(self):
        entry = self._entry(secret=SECRET)
        before = self.Log.search_count([("entry_id", "=", entry.id), ("event", "=", "reveal")])
        wizard_action = entry.action_reveal_secret()
        wizard = self.env["drkds.vault.reveal"].browse(wizard_action["res_id"])
        self.assertEqual(wizard.secret, SECRET)
        after = self.Log.search([("entry_id", "=", entry.id), ("event", "=", "reveal")])
        self.assertEqual(len(after), before + 1)
        self.assertEqual(after[0].user_id, self.env.user)
        self.assertNotIn(SECRET, str(after[0].note or ""))

    def test_storing_and_changing_a_secret_are_logged(self):
        entry = self._entry(secret=SECRET)
        self.assertEqual(
            self.Log.search_count([("entry_id", "=", entry.id), ("event", "=", "create")]), 1
        )
        entry.write({"secret": "rotated by hand"})
        self.assertEqual(
            self.Log.search_count([("entry_id", "=", entry.id), ("event", "=", "update")]), 1
        )

    def test_entry_without_a_secret_logs_nothing(self):
        entry = self.Entry.create([{"name": "Note only"}])[0]
        self.assertFalse(self.Log.search([("entry_id", "=", entry.id)]))
        with self.assertRaises(UserError):
            entry._read_secret()

    def test_closing_the_wizard_discards_the_plaintext(self):
        entry = self._entry(secret=SECRET)
        wizard = self.env["drkds.vault.reveal"].browse(
            entry.action_reveal_secret()["res_id"]
        )
        wizard.action_close()
        self.assertFalse(wizard.secret)

    def test_last_access_date_follows_the_log(self):
        entry = self._entry(secret=SECRET)
        self.assertFalse(entry.last_access_date)
        entry.action_reveal_secret()
        entry.invalidate_recordset()
        self.assertTrue(entry.last_access_date)

    def test_log_is_append_only_for_users(self):
        """Ordinary users may create log lines, never edit or delete them."""
        access = self.env["ir.model.access"].search([
            ("model_id.model", "=", "drkds.lite.vault.access.log"),
            ("group_id", "=", self.env.ref("base.group_user").id),
        ])
        self.assertTrue(access)
        self.assertTrue(all(a.perm_read and a.perm_create for a in access))
        self.assertFalse(any(a.perm_write or a.perm_unlink for a in access))
