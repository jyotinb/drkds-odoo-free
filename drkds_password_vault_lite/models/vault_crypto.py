"""Key management and authenticated encryption for the personal vault.

Design, stated plainly because the whole module is worth nothing without it:

* The cipher is **Fernet** from ``cryptography`` (AES-128-CBC for
  confidentiality plus HMAC-SHA256 for authenticity, with a random IV per
  message). Nothing here is hand-rolled, and a tampered ciphertext fails
  loudly instead of decrypting to rubbish.
* The key is **never stored in the database**. It comes from the deployment,
  in this order of precedence:

  1. the ``DRKDS_VAULT_KEY`` environment variable of the Odoo process,
  2. the ``drkds_vault_key`` entry in the Odoo configuration file
     (``odoo.conf``). Odoo 19 keeps unknown ``[options]`` keys verbatim, so
     no patch to Odoo is needed.

  An ``ir.config_parameter`` would NOT do: it is a row in the same database
  as the ciphertext, so anyone holding a database dump would hold both the
  lock and the key. Keeping the secret in the process environment or in a
  ``0600`` config file means a stolen dump alone is not enough.
* The configured value is a *master secret*, not the encryption key. The key
  actually used is derived per database with PBKDF2-HMAC-SHA256, 240 000
  iterations, salted with that database's ``database.uuid``. Two databases
  sharing one master secret therefore do not share a key, and a ciphertext
  lifted from one database cannot be decrypted inside another.
* If the master secret is missing, too short, or wrong, every read and write
  of a secret raises. The module never falls back to storing plaintext.

What an attacker with a database dump gets: entry names, URLs, usernames,
notes, folders, tags and the access log. Those are metadata and they are not
encrypted. What they do not get, without the master secret, is any password.
"""
import base64
import hashlib
import logging
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import config

_logger = logging.getLogger(__name__)

#: Environment variable checked before the configuration file.
KEY_ENV_VAR = "DRKDS_VAULT_KEY"

#: Key of the ``[options]`` entry read from ``odoo.conf``.
KEY_CONFIG_OPTION = "drkds_vault_key"

#: Shortest master secret accepted. A 32 character random string is the
#: floor; the manual tells deployers to paste ``Fernet.generate_key()``.
MIN_KEY_LENGTH = 32

#: PBKDF2 parameters. The info string is versioned so the derivation can be
#: changed later without silently producing a key that decrypts nothing.
KDF_ITERATIONS = 240_000
KDF_INFO = b"drkds_password_vault_lite/v1"

#: Derived keys cached per (database uuid, master secret digest). PBKDF2 at
#: this cost must not run on every field read.
_DERIVED_KEY_CACHE = {}


def master_secret():
    """Return the configured master secret, or raise.

    The value itself is never logged, never returned in an error message and
    never written anywhere.
    """
    raw = os.environ.get(KEY_ENV_VAR) or config.get(KEY_CONFIG_OPTION) or ""
    raw = raw.strip() if isinstance(raw, str) else ""
    if not raw:
        raise UserError(_(
            "The password vault is not configured. Set %(option)s in the Odoo "
            "configuration file, or the %(env)s environment variable, to a long "
            "random value and restart Odoo. Until then no secret can be stored "
            "or read: the vault refuses to keep passwords in clear text.",
            option=KEY_CONFIG_OPTION, env=KEY_ENV_VAR,
        ))
    if len(raw) < MIN_KEY_LENGTH:
        raise UserError(_(
            "The password vault key is too short: %(length)s characters, "
            "%(minimum)s required. Generate one with "
            "'python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\"'.",
            length=len(raw), minimum=MIN_KEY_LENGTH,
        ))
    return raw


def derive_key(secret, salt):
    """Derive a Fernet key from the master *secret* and a per-database *salt*."""
    cache_key = (salt, hashlib.sha256(secret.encode()).hexdigest())
    cached = _DERIVED_KEY_CACHE.get(cache_key)
    if cached:
        return cached
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=(KDF_INFO + salt.encode()),
        iterations=KDF_ITERATIONS,
    )
    derived = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
    _DERIVED_KEY_CACHE[cache_key] = derived
    return derived


class DrkdsVaultCrypto(models.AbstractModel):
    """Encryption service for the vault, kept apart from any stored model."""

    _name = "drkds.vault.crypto"
    _description = "Vault Encryption Service"

    def _vault_salt(self):
        """Return the per-database salt.

        ``database.uuid`` is created by ``base`` on install and is unique per
        database. It is not a secret and does not need to be: its job is to
        separate key material between databases, not to hide anything.
        """
        salt = self.env["ir.config_parameter"].sudo().get_param("database.uuid")
        if not salt:
            # Never seen on a normal install; refuse rather than fall back to
            # an empty salt that would make keys portable between databases.
            raise UserError(_(
                "The database has no 'database.uuid' system parameter, so no "
                "vault key can be derived. Refusing to store secrets."
            ))
        return salt

    def _fernet(self):
        """Return a configured :class:`Fernet`, or raise a clear error."""
        return Fernet(derive_key(master_secret(), self._vault_salt()))

    def _encrypt(self, plaintext):
        """Encrypt *plaintext* and return an ASCII Fernet token."""
        if plaintext is None or plaintext == "":
            return False
        if not isinstance(plaintext, str):
            raise UserError(_("Only text can be stored in the vault."))
        return self._fernet().encrypt(plaintext.encode()).decode()

    def _decrypt(self, token):
        """Return the plaintext behind a Fernet *token*.

        Raises on a wrong key or a tampered token. The token and the key are
        deliberately kept out of the message.
        """
        if not token:
            return ""
        try:
            return self._fernet().decrypt(token.encode()).decode()
        except InvalidToken:
            _logger.warning(
                "Vault: authentication failed while decrypting a secret "
                "(model %s, user %s). Wrong key or altered data.",
                self._name, self.env.uid,
            )
            raise UserError(_(
                "This secret cannot be decrypted. Either the vault key "
                "configured on this server is not the one it was encrypted "
                "with, or the stored value has been altered."
            )) from None

    def _self_check(self):
        """Round-trip a probe value so misconfiguration surfaces immediately."""
        probe = "drkds-vault-self-check"
        if self._decrypt(self._encrypt(probe)) != probe:
            raise UserError(_("The vault encryption self-check failed."))
        return True
