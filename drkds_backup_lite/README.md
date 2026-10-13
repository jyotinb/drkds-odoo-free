# Scheduled Database Backup (Lite)

Nightly database dumps to a local folder, with retention, a log and failure
alerts, on Odoo 19 Community.

Name a folder on the server, pick a format, say how many copies to keep, and
the database is dumped on the schedule you set. Every run, good or bad, is
written to a log. A failed run raises a to-do for the people you name.

## What you get

| Piece | What it does |
|---|---|
| Backup configuration | Name, folder, format, keep last N, users to notify on failure, schedule (every N hours / days / weeks, next run) |
| Scheduled action | One `ir.cron` per configuration, created with it, paused when it is archived, deleted with it |
| Formats | **Zip**: `dump.sql`, `manifest.json` and `filestore/`, restorable from the database manager. **Dump**: `pg_dump --format=c`, restorable with `pg_restore` |
| Retention | After a successful run, this database's backup files beyond the last N are removed from the folder and their log lines marked *Done (file removed)* |
| Backup run log | File, full path, format, started, duration, size, status (Done / Failed / Done (file removed)), message, and whether the file is still on disk |
| Backup Now | Runs the configuration at once and opens its log line |
| Test Folder | Tells you whether the Odoo system user can write to the folder |
| Failure alerts | A note in the configuration's chatter and a to-do activity for every notified user, with the reason |
| Settings | **Settings > Database Backup**: a default folder proposed to new configurations and a button to the configurations |

## Installation

Copy the module into your addons path, update the apps list and install
**Scheduled Database Backup (Lite)**. Depends on `base` and `mail` only.

Requirements on the server:

- `pg_dump` installed and on the `PATH` of the Odoo process, or named by
  `pg_path` in the Odoo configuration file. It should match the PostgreSQL
  server version.
- A folder that exists and is writable by the system user Odoo runs as
  (commonly `odoo`). For example:

      sudo mkdir -p /var/backups/odoo
      sudo chown odoo:odoo /var/backups/odoo
      sudo chmod 750 /var/backups/odoo

## Configuration

1. **Settings > Database Backup**: optionally set the default folder.
2. **Settings > Database Backup > Configurations > New**: name it, confirm the
   folder, choose the format and how many copies to keep, add the users to
   notify, and set the schedule: *Every 1 Days* with *Next Run* at the hour
   you want, in your time zone.
3. Click **Test Folder**. Fix the folder until it answers green.
4. Click **Backup Now** once, and open the log line to check the file.

Only administrators (the *Settings* access right) see the menus.

## Use

The cron does the work. **Settings > Database Backup > Runs** lists every
run with its file, size, duration and status; filter *Failed* to see what
went wrong, group by configuration or day.

The chatter on each configuration records every failure, and each notified
user finds a **Backup failed** to-do in their activities with the reason.
Mark it done once the cause is fixed.

## Behaviour worth knowing

- The dump is made by `pg_dump` using the database host, port, user and
  password Odoo itself is running with. The master password is not asked
  for and nothing is stored by the module beyond the folder path.
- Core's `dump_db` is gated on `list_db`; this module does not use it, so
  backups keep working on a server where database listing is turned off.
- Files are named `<database>_<YYYYMMDD_HHMMSS>.zip` or `.dump`, with the
  time in UTC. A file is written as `.part` and renamed on completion, so a
  half-written backup never looks like a finished one.
- Retention only looks at files matching that name pattern for the current
  database. Anything else in the folder is left alone. It runs only after a
  successful backup; a failing night never deletes the copies you still have.
  *Keep Last* 0 keeps everything.
- A zip includes the filestore (attachments). The size of the zip is the size
  of your database plus your attachments; keep an eye on disk space.
- Each configuration backs up the one database Odoo is running. For several
  databases, install the module in each.
- The temporary SQL file is written inside the backup folder, so the folder
  needs roughly twice the size of the dump free during a zip run.
- The Backup Now button runs in the web request; a very large database may
  exceed the request time limit. Prefer the scheduler for those.

## Not in this module

Local folder only. There is no remote target, no encryption and no restore
from the interface.

The drkds Backup app adds remote targets (SFTP, S3), encryption, restore from
the interface and multi-database schedules.

Part of the drkds Indian SME suite for Odoo 19 Community.
