# Changelog

## 19.0.1.0.0 - 2026-10-13

First release.

- Backup configurations with folder, format (zip with filestore, or
  PostgreSQL custom-format dump), keep-last retention, users to notify and a
  schedule held by a scheduled action created per configuration.
- Backup run log with file, path, format, start, duration, size, status and
  message; status moves to "Done (file removed)" when retention deletes
  the file.
- Backup Now and Test Folder buttons on the configuration form.
- Failure posts a chatter note and a to-do activity to each notified user.
- Settings block under General Settings with a default folder and a link to
  the configurations.
- Menus under Settings > Database Backup, for administrators only.
- Dump written with pg_dump through Odoo's own connection settings; no
  master password, no stored credential, no network call.
