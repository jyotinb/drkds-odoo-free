# Changelog

## 19.0.1.0.0 - 2026-10-13

First release.

- Backup configurations with folder, format (zip with filestore, or
  PostgreSQL custom-format dump), keep-last retention, administrators to
  notify and a schedule held by a scheduled action created per configuration;
  one folder per active configuration.
- Backup run log with file, path, format, start, duration, size, status
  (running, done, failed, file removed) and message; status moves to "Done (file removed)" when retention deletes
  the file.
- Backup Now and Test Folder buttons on the configuration form.
- Failure posts a chatter note and a to-do activity to each notified
  administrator; a run stopped half-way is closed as failed by the next run.
- Settings block under General Settings with a default folder and a link to
  the configurations.
- Menus under Settings > Database Backup, for administrators only.
- Dump written with pg_dump through Odoo's own connection settings; no
  master password, no stored credential, no network call.

### Fixed during review, before release

- Zip backups failed with "Access Denied" on a server with `list_db = False`:
  core's `dump_db_manifest` is gated on it too. The manifest is now written
  by the module.
- A backup larger than 2 GiB overflowed the integer size column after the
  file was written: no log line, no alert, no retention. Size is now a float.
- A folder inside Odoo's filestore made the zip copy its own archive until
  the disk was full; a folder inside an addons path exposed the backup to
  anyone through the static file route; `..` and symlinks were taken at face
  value. Such folders are refused on save and before every run, and the zip
  never archives its own folder.
- Two configurations in one folder deleted each other's backups through
  retention. Each active configuration now needs its own folder; Duplicate
  creates the copy archived.
- A scheduled run killed by `limit_time_real_cron` or a restart left no log
  line, no alert, and its partial files (up to the size of the database) in
  the folder. Runs now open a *Running* line, committed in scheduled runs,
  and the next run closes a stale one as failed, removes the partial files
  and alerts.
- Backup Now started a second dump while the scheduler was running the same
  configuration. It is now refused, and the scheduler skips a configuration
  while Backup Now runs it.
- An operating-system error was logged as its bare number ("28" for a full
  disk). The message now carries the text, and the database password is
  masked should a tool ever print it.
- A folder Odoo could write but not list made a successful run raise during
  retention; the run is now kept and the log says retention could not run.
- Plain users could be named for failure alerts, receiving to-dos and emails
  about a record they cannot open. Only administrators can now be named, and
  someone who lost the right is skipped.
- Test Folder reported an access error as a failed folder check, and an
  administrator could rewrite a run's status or message through RPC. Both
  buttons now check access, and run lines can no longer be edited (only
  deleted).
