{
    "name": "Password Vault (Lite)",
    "summary": "A personal encrypted vault for credentials, inside your own Odoo database",
    "description": """
Password Vault (Lite)
=====================

A personal place to keep the logins a business runs on - the bank portal, the
courier account, the domain registrar - inside the Odoo database you already
operate, instead of a spreadsheet named *passwords.xlsx*.

How the encryption works
------------------------
* Secrets are encrypted with **Fernet** from the ``cryptography`` library that
  ships with Odoo: AES-128-CBC with an HMAC-SHA256 authentication tag and a
  random IV per value. No home-made cipher, no base64 pretending to be one.
* **The key is not in the database.** It is read from the ``DRKDS_VAULT_KEY``
  environment variable or from ``drkds_vault_key`` in ``odoo.conf``. A system
  parameter would sit in the same dump as the ciphertext and protect nothing.
* The configured value is a master secret. The key in use is derived from it
  per database with PBKDF2-HMAC-SHA256, 240 000 iterations, salted with that
  database's ``database.uuid``, so a ciphertext moved to another database
  cannot be opened there.
* If the key is missing, too short or wrong, the vault **raises**. It never
  falls back to storing a password in clear text.

What the module gives you
-------------------------
* Entries with a title, URL, username, encrypted password, notes, a folder and
  tags.
* A password field that is write-only: you type a new value in, it is never
  read back into a form, a list, a search or an export.
* An explicit **Reveal** action that shows the password once, in a dialog.
* An access log line for every secret stored, changed or revealed.
* Record rules that make an entry visible to its owner and to nobody else,
  administrators included.

Being honest about the threat model
-----------------------------------
Record rules are enforced by the Odoo ORM. A PostgreSQL superuser, or anyone
who can run arbitrary server-side Python on this instance, can read every row
of every table and can also read the key from the process environment. What
encryption at rest protects you against is a stolen database dump, a leaked
backup file, or a replica handed to a third party: those contain ciphertext
and a salt, and no key. Entry names, URLs, usernames, notes, folders, tags and
the access log are metadata and are not encrypted.

Not in this module
------------------
Sharing entries with colleagues, team vaults, rotation reminders and strength
auditing are deliberately absent. What is here is a personal vault, complete.

The drkds Credential Vault app adds team vaults, controlled sharing, rotation
reminders and password strength auditing.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "author": "drkds",
    "website": "https://drkdsinfo.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "external_dependencies": {"python": ["cryptography"]},
    "data": [
        "security/ir.model.access.csv",
        "security/drkds_vault_security.xml",
        "views/drkds_vault_entry_views.xml",
        "views/drkds_vault_support_views.xml",
        "wizard/drkds_vault_reveal_views.xml",
        "views/drkds_vault_menus.xml",
    ],
    "images": ["static/description/cover.png"],
    "installable": True,
    "application": True,
    "auto_install": False,
}
