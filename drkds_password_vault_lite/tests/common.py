"""Shared setup: a known vault key for the duration of the tests.

The key is injected into ``odoo.tools.config`` exactly the way a deployer
would put it in ``odoo.conf``, so the tests exercise the real lookup path.
"""
from odoo.tests import TransactionCase
from odoo.tools import config

from ..models import vault_crypto

#: A 44 character urlsafe-base64 value, the shape of ``Fernet.generate_key()``.
TEST_MASTER_KEY = "iQ8n2vP0Lr5TfJwXyZ3aB6cD9eG1hK4mN7pQsRtUvWx="
OTHER_MASTER_KEY = "Zx9W8v7U6t5S4r3Q2p1N0m9K8h7G6e5D4c3B2a1Z0y8="


class VaultCase(TransactionCase):
    """Base case with a configured vault key and a second, unrelated user."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._set_key(TEST_MASTER_KEY)
        cls.Entry = cls.env["drkds.vault.entry"]
        cls.Log = cls.env["drkds.vault.access.log"]
        cls.other_user = cls.env["res.users"].create([{
            "name": "Vault Outsider",
            "login": "vault.outsider@example.com",
            "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
        }])[0]

    @classmethod
    def _set_key(cls, value):
        """Set (or clear, with ``None``) the configured master secret."""
        if value is None:
            config.options.pop(vault_crypto.KEY_CONFIG_OPTION, None)
        else:
            config.options[vault_crypto.KEY_CONFIG_OPTION] = value
        vault_crypto._DERIVED_KEY_CACHE.clear()

    def setUp(self):
        super().setUp()
        self.addCleanup(self._set_key, TEST_MASTER_KEY)

    def _entry(self, secret="correct horse battery staple", **vals):
        return self.Entry.create([dict(
            {"name": "Bank portal", "username": "acct", "secret": secret}, **vals
        )])[0]
