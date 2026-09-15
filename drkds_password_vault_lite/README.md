# Password Vault (Lite)

A personal encrypted vault for credentials, inside your own Odoo database.

Every business keeps logins that live nowhere in Odoo: the bank portal, the
courier account, the domain registrar. This module gives each user a private
vault in the database you already run and back up, with passwords encrypted at
rest under a key kept deliberately outside that database.

## Before you install: set the key

The vault will not store anything until a key is configured. Generate one:

```
python -c \
  "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Put it in `odoo.conf`:

```
[options]
drkds_vault_key = <the value you just generated>
```

or export it for the Odoo process instead, which keeps it out of the file
altogether:

```
DRKDS_VAULT_KEY=<the value>
```

Restart Odoo. Keep `odoo.conf` at mode `0600`, and back the key up somewhere
that is not the database backup.

## How the encryption works

* **Cipher** — Fernet from `cryptography`, the library Odoo already ships:
  AES-128-CBC for confidentiality, HMAC-SHA256 for authenticity, a fresh random
  IV per value. Nothing in this module is a home-made cipher, and base64 is not
  mistaken for encryption anywhere.
* **Key location** — the environment variable `DRKDS_VAULT_KEY` first, then
  `drkds_vault_key` in `odoo.conf`. Odoo 19 keeps unknown `[options]` keys
  verbatim, so no patch to Odoo is needed.
* **Why not `ir.config_parameter`** — because it is a row in the same database
  as the ciphertext. Anyone holding a dump would hold the lock and the key
  together, and the encryption would be decoration.
* **Key derivation** — the configured value is a master secret, not the key.
  The key in use is derived per database with PBKDF2-HMAC-SHA256, 240 000
  iterations, salted with that database's `database.uuid`. Two databases
  sharing a master secret do not share a key, and a ciphertext moved between
  them will not open.
* **Failure is loud** — missing key, short key, wrong key or altered ciphertext
  all raise a clear error. There is no path in this module that stores a
  password in clear text, and none that returns a wrong plaintext.

## What it does

* Entries with a title, URL, username, encrypted password, notes, a folder and
  tags.
* A write-only password field: it is not stored in the ORM read path, cannot be
  searched on, and is excluded from exports.
* An explicit **Reveal** action showing the password once, in a dialog.
* An access log line for every secret stored, changed or revealed. Ordinary
  users can read and append to it; they cannot edit or delete it.
* Global record rules limiting entries, folders, tags and log lines to their
  owner. There is no manager group and no administrator override.

## Being honest about the threat model

What encryption at rest buys you here is protection against a **stolen dump, a
leaked backup file, or a replica handed to a third party**: those contain
ciphertext and a salt and no key.

What it does not buy you:

* A **PostgreSQL superuser** can read every row of every table. Record rules
  live in the Odoo ORM and are not enforced by the database.
* Anyone who can run **arbitrary server-side Python** on the instance, or read
  the process environment, can read the key and therefore every secret.
* Titles, URLs, usernames, **notes**, folders, tags and the access log are
  metadata and are **not encrypted**. Keep passwords out of the notes field.
* **Lose the key and the passwords are gone.** There is no recovery path and
  none will be added; a recovery path is a second key.

## Not in this module

Sharing entries with colleagues, shared team vaults, rotation reminders and
password strength auditing are deliberately absent. What is here is a personal
vault, complete.

The drkds Credential Vault app adds team vaults, controlled sharing, rotation
reminders and password strength auditing.

Part of the drkds Indian SME suite for Odoo 19 Community.
