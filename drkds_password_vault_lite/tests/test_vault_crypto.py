"""Tests about the cipher and the key, the part that has to be right."""
import os
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import config

from ..models import vault_crypto
from .common import OTHER_MASTER_KEY, TEST_MASTER_KEY, VaultCase


@tagged("post_install", "-at_install")
class TestVaultCrypto(VaultCase):

    # -- round trip ----------------------------------------------------
    def test_encrypt_decrypt_round_trip(self):
        """Whatever goes in comes back out, including awkward characters."""
        crypto = self.env["drkds.vault.crypto"]
        for plaintext in ("s3cr3t", "à la mode ✓", "x" * 4096, "'; DROP TABLE --"):
            with self.subTest(plaintext=plaintext[:16]):
                self.assertEqual(crypto._decrypt(crypto._encrypt(plaintext)), plaintext)

    def test_ciphertext_differs_every_time(self):
        """A random IV means the same password never has the same token."""
        crypto = self.env["drkds.vault.crypto"]
        first, second = crypto._encrypt("same"), crypto._encrypt("same")
        self.assertNotEqual(first, second, "Fernet must not be deterministic")
        self.assertEqual(crypto._decrypt(first), crypto._decrypt(second))

    def test_empty_secret_is_not_encrypted(self):
        crypto = self.env["drkds.vault.crypto"]
        self.assertFalse(crypto._encrypt(""))
        self.assertEqual(crypto._decrypt(False), "")

    # -- key management ------------------------------------------------
    def test_missing_key_fails_loudly(self):
        """No key configured: creating a secret raises, nothing is stored.

        This is the test that matters most. A vault that silently keeps
        plaintext when misconfigured is worse than no vault at all.
        """
        self._set_key(None)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(vault_crypto.KEY_ENV_VAR, None)
            with self.assertRaises(UserError):
                self._entry(secret="never stored")
        self._set_key(TEST_MASTER_KEY)
        self.assertFalse(
            self.Entry.search([("name", "=", "Bank portal")]),
            "no row may survive a failed encryption",
        )

    def test_short_key_is_refused(self):
        """A short passphrase is rejected instead of being stretched anyway."""
        self._set_key("hunter2")
        with self.assertRaises(UserError):
            self.env["drkds.vault.crypto"]._encrypt("anything")

    def test_blank_key_counts_as_missing(self):
        self._set_key("   ")
        with self.assertRaises(UserError):
            vault_crypto.master_secret()

    def test_environment_variable_wins_over_config(self):
        """A deployer can keep the key out of the config file entirely."""
        self._set_key("config-side-key-that-is-long-enough-xx")
        with patch.dict(os.environ, {vault_crypto.KEY_ENV_VAR: TEST_MASTER_KEY}):
            self.assertEqual(vault_crypto.master_secret(), TEST_MASTER_KEY)

    def test_key_is_never_stored_in_the_database(self):
        """The master secret appears in no system parameter and no vault row."""
        entry = self._entry(secret="top secret")
        self.env.flush_all()
        params = self.env["ir.config_parameter"].sudo().search([])
        self.assertFalse(
            [p for p in params if TEST_MASTER_KEY in (p.value or "")],
            "the key must never be written to ir.config_parameter",
        )
        self.env.cr.execute(
            "SELECT secret_encrypted FROM drkds_lite_vault_entry WHERE id = %s", (entry.id,)
        )
        self.assertNotIn(TEST_MASTER_KEY, self.env.cr.fetchone()[0])

    def test_wrong_key_raises_instead_of_returning_garbage(self):
        """Authenticated encryption: a different key is detected, not guessed at."""
        entry = self._entry(secret="opensesame")
        self._set_key(OTHER_MASTER_KEY)
        with self.assertRaises(UserError):
            entry._read_secret()

    def test_tampered_ciphertext_is_rejected(self):
        """Editing the token in the database makes it unreadable, not wrong."""
        entry = self._entry(secret="opensesame")
        self.env.flush_all()
        token = entry.secret_encrypted
        tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
        self.env.cr.execute(
            "UPDATE drkds_lite_vault_entry SET secret_encrypted = %s WHERE id = %s",
            (tampered, entry.id),
        )
        entry.invalidate_recordset()
        self.assertNotEqual(entry.secret_encrypted, token)
        with self.assertRaises(UserError):
            entry._read_secret()

    def test_key_is_derived_per_database(self):
        """The database uuid is part of the derivation, so keys do not travel."""
        first = vault_crypto.derive_key(TEST_MASTER_KEY, "uuid-one")
        second = vault_crypto.derive_key(TEST_MASTER_KEY, "uuid-two")
        self.assertNotEqual(first, second)
        self.assertEqual(first, vault_crypto.derive_key(TEST_MASTER_KEY, "uuid-one"))

    def test_config_option_is_readable_from_odoo_conf(self):
        """Odoo 19 keeps unknown [options] keys, which is what we rely on."""
        self.assertEqual(
            config.get(vault_crypto.KEY_CONFIG_OPTION), TEST_MASTER_KEY
        )
