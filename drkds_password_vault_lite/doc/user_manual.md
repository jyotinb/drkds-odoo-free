# Password Vault (Lite) — user manual

## 1. One-time setup by whoever runs the server

Nothing can be stored until a vault key exists. This is intentional: a vault
that works without a key is a vault that keeps plaintext.

1. Generate a key:

   ```
   /opt/odoo19/odoo19-venv/bin/python -c \
     "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

2. Add it to `odoo.conf`, under `[options]`:

   ```
   drkds_vault_key = <the generated value>
   ```

   or set `DRKDS_VAULT_KEY` in the environment of the Odoo process, which is
   preferable when the config file is under version control. The environment
   variable wins if both are present.

3. `chmod 0600 odoo.conf`, restart Odoo.

4. Store a copy of the key somewhere that is **not** the database backup — a
   password manager, a sealed envelope, your cloud provider's secret store. If
   you restore a database on a server without the key, the entries survive but
   the passwords cannot be read. There is no recovery path.

A key of fewer than 32 characters is refused rather than stretched anyway.

## 2. Daily use

**Password Vault → My Vault** shows your entries and nobody else's.

### Adding an entry

Create, then fill in:

| Field | Notes |
| --- | --- |
| Title | What this login is, e.g. "HDFC current account" |
| Username | The login name |
| Password | Type it here. It is encrypted on save |
| URL | Where the credentials are used |
| Folder | Optional grouping, personal to you |
| Tags | Optional labels, personal to you |
| Notes | **Stored in clear text.** No passwords here |

Save. The Password field goes blank and stays blank: it is write-only by
design, so a password is never sent back to a browser by accident, never lands
in a list view, and never appears in an export.

### Seeing a password again

Open the entry and click **Reveal Password**. A dialog shows it once. Closing
the dialog discards it.

Every reveal writes a line in the access log with your name and the time. So do
storing a password for the first time and changing it. **Password Vault →
Access Log** shows your own history; the stat button on an entry shows just
that entry's.

### Changing a password

Type the new value in the Password field and save. The old ciphertext is
replaced; there is no version history, and nothing keeps the previous value.

### Duplicating an entry

Duplicate carries the title, URL, username, notes, folder and tags. It never
carries the password.

## 3. Who can see what

Entries, folders, tags and access log lines are restricted to their owner by
global record rules. There is no vault manager group and no administrator
override, so another user — including the Odoo administrator — does not see
your entries in a list, cannot read them through the ORM, and cannot reveal
them.

Be clear about the limit of that statement. Record rules are enforced by the
Odoo ORM:

* a **PostgreSQL superuser** can read every row directly, and will see
  ciphertext for the passwords and plain values for everything else;
* anyone who can run **server-side Python** on this instance, or read the Odoo
  process environment, can obtain the key and therefore every password.

Encryption at rest is aimed at a different attacker: the one who ends up with
a database dump, a backup file or a replica, and no key.

## 4. When something goes wrong

| Message | What it means |
| --- | --- |
| "The password vault is not configured" | No key in the environment or in `odoo.conf`. Nothing was stored |
| "The password vault key is too short" | Under 32 characters. Generate a proper one |
| "This secret cannot be decrypted" | The server's key is not the one this entry was encrypted with, or the stored value was altered. Restore the right key |

None of these fall back to plaintext, and none of them print the key, the
password or the ciphertext.

## 5. Not in this module

Sharing entries with colleagues, shared team vaults, rotation reminders and
password strength auditing are deliberately absent.

The drkds Password Vault app adds team vaults, controlled sharing, rotation
reminders and password strength auditing.

Part of the drkds Indian SME suite for Odoo 19 Community.
