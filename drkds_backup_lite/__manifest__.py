{
    "name": "Scheduled Database Backup (Lite)",
    "summary": "Nightly database dumps to a local folder, with retention, a log and failure alerts, on Odoo 19 Community",
    "description": """
Scheduled Database Backup (Lite)
================================

A scheduled dump of the current database to a folder on the server, for
Odoo 19 Community. Set a folder, pick a format, say how many copies to keep,
and the cron does the rest. Every run, good or bad, is written to a log,
and a failed run raises a to-do for the administrators you name.

What it gives you
-----------------
* **Backup configurations** - a name, the target folder, the format, how
  many files to keep, who to tell when it fails, and the schedule. Each
  configuration owns its own scheduled action and its own folder.
* **Two formats** - a zip holding ``dump.sql``, ``manifest.json`` and the
  filestore, which the database manager can restore as it is; or a plain
  PostgreSQL custom-format dump for ``pg_restore``.
* **Retention** - after each run the oldest files beyond the last N are
  removed from the folder, and their log lines are marked as such.
* **A log per run** - file, size, duration, status and message. Nothing
  disappears silently: a run stopped half-way by a time limit or a restart
  is closed as failed by the next run, which removes its partial files.
* **Backup now** - run a configuration on demand and land on its log.
* **Test folder** - check that the Odoo system user can write to the
  folder before the night comes.
* **Failure alerts** - a failed run posts a to-do activity to the notified
  administrators and a note in the configuration's chatter.

Notes
-----
The dump is produced by ``pg_dump`` with the connection settings Odoo is
already running with. No master password is asked for, none is stored, and
nothing is sent anywhere. It works with database listing turned off. The
folder must be writable by the system user that runs Odoo, and may not be
inside the filestore or an addons path.

The paid drkds Backup Manager app adds SFTP and second-copy targets, retention by count and age, sha256 integrity checks, email summaries and a restore helper.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Administration",
    "author": "drkds",
    "website": "https://drkdsinfo.com",
    "support": "jyotinboghani@gmail.com",
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/drkds_backup_log_views.xml",
        "views/drkds_backup_config_views.xml",
        "views/res_config_settings_views.xml",
        "views/drkds_backup_menus.xml",
    ],
    "images": [
        "static/description/screenshot_01.png",
        "static/description/screenshot_02.png",
        "static/description/screenshot_03.png",
        "static/description/screenshot_04.png",
        "static/description/screenshot_05.png",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
