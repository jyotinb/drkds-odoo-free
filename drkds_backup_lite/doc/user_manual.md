# Scheduled Database Backup (Lite) — user manual

## 1. Prepare the server

The module writes files on the machine where Odoo runs, as the system user
that runs Odoo. Before anything else:

1. Make sure `pg_dump` is installed there (`which pg_dump`). If it lives
   outside the `PATH`, set `pg_path = /usr/lib/postgresql/16/bin` (or
   wherever it is) in the Odoo configuration file and restart Odoo.
2. Create the folder and give it to the Odoo user:

       sudo mkdir -p /var/backups/odoo
       sudo chown odoo:odoo /var/backups/odoo
       sudo chmod 750 /var/backups/odoo

   Replace `odoo` with the user Odoo actually runs as.

Only users with the **Settings** access right (Administration: Settings)
see the backup menus.

## 2. Set a default folder (optional)

**Settings > Database Backup**: type the folder in **Default Backup Folder**
and save. New configurations propose it.

## 3. Create a configuration

**Settings > Database Backup > Configurations > New**.

| Field | Meaning |
|---|---|
| Name | How you will recognise it, e.g. *Nightly* |
| Database | The database being backed up: the one you are logged into |
| Backup Folder | Absolute path on the server, see above |
| Format | **Zip**: `dump.sql`, `manifest.json` and the filestore, restorable from `/web/database/manager`. **Dump**: `pg_dump` custom format for `pg_restore` (no attachments) |
| Keep Last | How many backup files of this database to keep in the folder. 0 keeps all |
| Every / Interval Unit | How often the scheduler runs it |
| Next Run | When it runs next; set it to the quiet hour you want, in your time zone. After each run it moves forward by the interval |
| Notify on Failure | Users who get a to-do when a run fails. You are proposed |

Save. The module creates a scheduled action named *Database backup: Nightly*
for this configuration; you can see it in developer mode under
**Scheduled Action** on the form, and in Settings > Technical > Scheduled
Actions. Edit the schedule here or there, it is the same record.

## 4. Test the folder

Click **Test Folder**. A green notification means Odoo created and removed a
probe file in the folder. A red one names the reason: the folder does not
exist, is not writable by the Odoo system user, or a file could not be
created there. Fix it on the server and try again.

## 5. Run one now

Click **Backup Now** and confirm. When it is done you land on the run's log
line: the file name, full path, size, how long it took, and the status.

A large database can take minutes; the button runs within the web request
and may hit the request time limit on very large databases. If so, let the
scheduler do it.

## 6. Read the log

**Settings > Database Backup > Runs** lists every run, newest first.

| Status | Meaning |
|---|---|
| Done | The file is in the folder |
| Failed | No file was written; the message says why |
| Done (file removed) | The run succeeded and a later run's retention removed the file |

**File Present** tells you whether the file is on disk right now, which
catches a backup removed by hand or a folder that was moved.

The **Runs** button on a configuration shows only its own runs.

## 7. When a run fails

Three things happen:

1. The run is logged as *Failed* with the reason.
2. A note goes into the configuration's chatter.
3. Every user in **Notify on Failure** gets a **Backup failed** to-do
   activity on the configuration, with the reason in it.

Nothing is deleted by retention after a failure. Fix the cause (**Test
Folder** helps), run **Backup Now** to confirm, and mark the to-do done.

Typical causes: the folder vanished or lost its permissions, the disk is
full, `pg_dump` is missing or of the wrong version, or the database is
too large for the scheduler's time limit (`limit_time_real_cron`).

## 8. Retention

After each successful run, the module lists the files in the folder named
`<database>_<YYYYMMDD_HHMMSS>.zip` or `.dump` for this database, sorts them
newest first, and removes those beyond **Keep Last**. Their log lines move
to *Done (file removed)*, and the new run's message lists what was removed.
Other files in the folder, including other databases' backups, are never
touched.

## 9. Pause, resume, delete

- **Archive** the configuration (Action menu) to pause its schedule;
  unarchive to resume.
- **Delete** it to remove the scheduled action and its log lines. The
  backup files in the folder stay.
- **Duplicate** it to get a second configuration with its own schedule, for
  example a zip every night and a dump every week into another folder.

## 10. Restore

- **Zip**: open `/web/database/manager`, choose *Restore Database*, upload
  the zip. Or unzip it and run `psql newdb < dump.sql`, then move
  `filestore/` to the Odoo data directory under `filestore/newdb`.
- **Dump**: `createdb newdb && pg_restore --no-owner -d newdb file.dump`.
  Attachments are not in a dump; copy the filestore separately.

Restoring is done outside the module.
