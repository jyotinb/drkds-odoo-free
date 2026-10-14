# Scheduled Database Backup (Lite)

Nightly database dumps to a local folder, with retention, a log and failure
alerts, on Odoo 19 Community.

Name a folder on the server, pick a format, say how many copies to keep, and
the database is dumped on the schedule you set. Every run, good or bad, is
written to a log. A failed run raises a to-do for the people you name.

## What you get

| Piece | What it does |
|---|---|
| Backup configuration | Name, folder, format, keep last N, administrators to notify on failure, schedule (every N minutes, hours, days, weeks or months, and the next run) |
| Scheduled action | One `ir.cron` per configuration, created with it, paused when it is archived, deleted with it |
| Formats | **Zip**: `dump.sql`, `manifest.json` and `filestore/`, restorable from the database manager. **Dump**: `pg_dump --format=c`, restorable with `pg_restore` |
| Retention | After a successful run, this database's backup files beyond the last N are removed from the folder and their log lines marked *Done (file removed)* |
| Backup run log | File, full path, format, started, duration, size, status (Running / Done / Failed / Done (file removed)), message, and whether the file is still on disk |
| Backup Now | Runs the configuration at once and opens its log line |
| Test Folder | Tells you whether the Odoo system user can write to the folder |
| Failure alerts | A note in the configuration's chatter and a to-do activity for every notified administrator, with the reason. A run stopped half-way is reported by the next run |
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

1. **Settings > Database Backup**: optionally set the default folder. It is
   proposed to every new configuration; each active one needs its own folder,
   so change it from the second configuration on.
2. **Settings > Database Backup > Configurations > New**: name it, confirm the
   folder, choose the format and how many copies to keep, add the users to
   notify (administrators only), and set the schedule: *Every 1 Days* with
   *Next Run* at the hour you want, in your time zone.
3. Click **Test Folder**. Fix the folder until it answers green.
4. Click **Backup Now** once, and open the log line to check the file.

Only administrators (the *Settings* access right) see the menus.

## Use

The cron does the work. **Settings > Database Backup > Runs** lists every
run with its file, size, duration and status; filter *Failed* to see what
went wrong, group by configuration or day.

The chatter on each configuration records every failure, and each notified
administrator finds a **Backup failed** to-do in their activities with the
reason. A run still shown as *Running* is in progress, or was stopped and
will be closed by the next run.
Mark it done once the cause is fixed.

## Behaviour worth knowing

- The dump is made by `pg_dump` using the database host, port, user and
  password Odoo itself is running with. The master password is not asked
  for and nothing is stored by the module beyond the folder path.
- Core's `dump_db` and `dump_db_manifest` are gated on `list_db`; this
  module uses neither (it writes the same `manifest.json` itself), so backups
  keep working on a server where database listing is turned off.
- The folder must be an absolute path without `..`, and may not be (or lead,
  through a symlink, to) a place inside Odoo's filestore or any addons path.
  Inside the filestore a zip would copy its own archive until the disk is
  full; inside an addons path the files of every module's `static` folder are
  served to anyone. The rule is checked on save and again before every run.
- Each active configuration needs its own folder. Retention keeps the last N
  backups of this database in a folder, so two configurations sharing one
  would delete each other's copies. **Duplicate** therefore creates the copy
  archived: give it its own folder (a subfolder is fine), then unarchive it.
- Every run opens its log line as *Running*. If the scheduler's worker is
  stopped half-way (the `limit_time_real_cron` time limit, a restart, a
  crash), the next run of that configuration marks the line *Failed*
  ("Interrupted"), removes the partial files and alerts the notified
  administrators. Odoo retries a killed scheduled job straight away, so this
  usually shows within minutes.
- A configuration runs once at a time. **Backup Now** is refused while the
  scheduler is running it, and the scheduler waits while Backup Now runs.
  While a run is in progress, the configuration's name, schedule and
  archiving cannot be changed (Odoo locks the scheduled action); the other
  fields can.
- Odoo's scheduler moves *Next Run* forward by the interval in UTC. Where
  your time zone observes daylight saving time, the local hour of the run
  shifts by one hour when the clocks change; adjust *Next Run* if that
  matters. India has no daylight saving time.
- The file size is stored as a float, so backups larger than 2 GiB are
  logged like any other.
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
- The models are `drkds.backup.lite.config` and `drkds.backup.lite.log`,
  names no other drkds module uses, so it can be installed in the same
  database as the other drkds backup module; each keeps its own
  configurations, runs and scheduled actions.
- The temporary SQL file is written inside the backup folder, so the folder
  needs roughly twice the size of the dump free during a zip run.
- The Backup Now button runs in the web request; a very large database may
  exceed the request time limit. The error then shows on screen, no log line
  is kept, and the next run removes the partial files. Prefer the scheduler
  for those.

## Not in this module

Local folder only. There is no remote target, no encryption and no restore
from the interface.

The paid drkds Backup Manager app adds SFTP and second-copy targets, retention by count and age, sha256 integrity checks, email summaries and a restore helper.

Part of the drkds Indian SME suite for Odoo 19 Community.
