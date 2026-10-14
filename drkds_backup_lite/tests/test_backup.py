import json
import os
import stat
import zipfile
from unittest.mock import patch

from psycopg2 import IntegrityError

from odoo import release, tools
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import CONFIG_LOGGER, BackupCommon


@tagged("post_install", "-at_install")
class TestBackupDump(BackupCommon):
    def test_zip_contains_dump_sql_and_manifest(self):
        config = self._config()
        log = config._run_backup()

        self.assertEqual(log.status, "done", log.message)
        self.assertEqual(log.config_id, config)
        self.assertEqual(log.folder, self.folder)
        self.assertRegex(log.name, r"^%s_\d{8}_\d{6}\.zip$" % self.env.cr.dbname)
        path = os.path.join(self.folder, log.name)
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(log.size, os.path.getsize(path))
        self.assertGreater(log.size, 0)
        self.assertGreater(log.duration, 0)
        self.assertTrue(log.file_exists)
        self.assertEqual(log.path, path)
        self.assertEqual(self._backup_files(), [log.name])
        self.assertFalse(os.path.exists(path + ".part"))

        self.assertTrue(zipfile.is_zipfile(path))
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            self.assertEqual(names[0], "dump.sql", "dump.sql must be the first member")
            self.assertIn("manifest.json", names)
            manifest = json.loads(archive.read("manifest.json"))
            sql_head = archive.read("dump.sql")[:4096].decode("utf-8", "replace")
        self.assertIn("PostgreSQL database dump", sql_head)
        self.assertEqual(manifest["odoo_dump"], "1")
        self.assertEqual(manifest["db_name"], self.env.cr.dbname)
        self.assertIn("drkds_backup_lite", manifest["modules"])
        self.assertIn("base", manifest["modules"])
        self.assertEqual(manifest["major_version"], release.major_version)
        self.assertEqual(manifest["version"], release.version)

    def test_zip_includes_filestore_files(self):
        """The attachment store goes into the zip under filestore/, as the
        database manager expects it on restore."""
        attachment = self.env["ir.attachment"].create({
            "name": "note.txt", "raw": b"keep me", "res_model": "drkds.backup.lite.config", "res_id": 0,
        })
        self.assertTrue(attachment.store_fname, "attachment must be on disk, not in the table")
        config = self._config()
        log = config._run_backup()
        self.assertEqual(log.status, "done", log.message)
        with zipfile.ZipFile(log.path) as archive:
            self.assertIn("filestore/" + attachment.store_fname, archive.namelist())

    def test_dump_format_writes_pg_custom_archive(self):
        config = self._config(backup_format="dump")
        log = config._run_backup()
        self.assertEqual(log.status, "done", log.message)
        self.assertRegex(log.name, r"\.dump$")
        with open(log.path, "rb") as fh:
            self.assertEqual(fh.read(5), b"PGDMP", "pg_dump custom format magic")
        self.assertFalse(zipfile.is_zipfile(log.path))

    def test_two_runs_in_one_second_get_distinct_names(self):
        config = self._config()
        first, second = config._next_file_name(self.folder)[0], None
        self._touch(first)
        second = config._next_file_name(self.folder)[0]
        self.assertNotEqual(first, second)
        self.assertTrue(config._file_pattern().match(second))
        self.assertGreater(second, first)

    def test_backup_now_opens_the_log(self):
        config = self._config()
        action = config.with_user(self.admin).action_backup_now()
        self.assertEqual(action["res_model"], "drkds.backup.lite.log")
        log = self.Log.browse(action["res_id"])
        self.assertEqual(log.status, "done", log.message)
        self.assertEqual(config.log_count, 1)
        self.assertEqual(config.last_status, "done")
        self.assertEqual(config.last_run, log.date_start)


@tagged("post_install", "-at_install")
class TestBackupRetention(BackupCommon):
    def test_retention_keeps_last_n(self):
        """Three stale files plus a fresh run with keep_last=2: the two
        newest survive, the fresh one among them, and nothing else is touched."""
        db = self.env.cr.dbname
        stale = ["%s_20260101_020000.zip" % db, "%s_20260102_020000.zip" % db,
                 "%s_20260103_020000.dump" % db]
        for name in stale:
            self._touch(name)
        self._touch("%s_manual.zip" % db)
        self._touch("other_db_20260104_020000.zip")
        config = self._config(keep_last=2)
        old_logs = self.Log.create([{
            "config_id": config.id, "name": name, "folder": self.folder,
            "status": "done", "date_start": "2026-01-0%d 02:00:00" % (i + 1),
        } for i, name in enumerate(stale)])

        log = config._run_backup()

        self.assertEqual(log.status, "done", log.message)
        kept = self._backup_files()
        self.assertEqual(len(kept), 2)
        self.assertEqual(kept, [stale[2], log.name])
        self.assertIn("Removed by retention", log.message)
        self.assertIn(stale[0], log.message)
        self.assertIn(stale[1], log.message)
        listing = os.listdir(self.folder)
        self.assertIn("%s_manual.zip" % db, listing)
        self.assertIn("other_db_20260104_020000.zip", listing)
        self.assertEqual(old_logs.mapped("status"), ["deleted", "deleted", "done"])
        self.assertFalse(old_logs[0].file_exists)
        self.assertTrue(old_logs[2].file_exists)

    def test_keep_last_zero_keeps_everything(self):
        db = self.env.cr.dbname
        for day in range(1, 6):
            self._touch("%s_2026010%d_020000.zip" % (db, day))
        config = self._config(keep_last=0)
        log = config._run_backup()
        self.assertEqual(log.status, "done", log.message)
        self.assertEqual(len(self._backup_files()), 6)
        self.assertFalse(log.message)

    def test_retention_not_applied_after_failure(self):
        db = self.env.cr.dbname
        for day in range(1, 4):
            self._touch("%s_2026010%d_020000.zip" % (db, day))
        config = self._config(keep_last=1)
        with patch(CONFIG_LOGGER + ".find_pg_tool", return_value="/bin/false"), \
                mute_logger(CONFIG_LOGGER):
            log = config._run_backup()
        self.assertEqual(log.status, "failed")
        self.assertEqual(len(self._backup_files()), 3, "a failed run must not delete old copies")

    def test_keep_last_negative_rejected(self):
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            self._config(keep_last=-1)


@tagged("post_install", "-at_install")
class TestBackupFailure(BackupCommon):
    def test_unwritable_folder_logs_failure_and_notifies(self):
        if os.geteuid() == 0:
            self.fail("run the tests as the Odoo system user, root can write anywhere")
        config = self._config()
        os.chmod(self.folder, stat.S_IRUSR | stat.S_IXUSR)

        with mute_logger(CONFIG_LOGGER):
            log = config._run_backup()

        self.assertEqual(log.status, "failed")
        self.assertIn("not writable", log.message)
        self.assertEqual(log.size, 0)
        self.assertFalse(log.file_exists)
        self.assertEqual(os.listdir(self.folder), [], "nothing may be left behind")
        self.assertEqual(config.last_status, "failed")

        activities = self._todo_activities(config)
        self.assertEqual(activities.user_id, self.admin | self.watcher)
        self.assertEqual(len(activities), 2)
        for activity in activities:
            self.assertEqual(activity.summary, "Backup failed: Nightly")
            self.assertIn("not writable", activity.note)
        note = config.message_ids.filtered(lambda m: "failed" in (m.body or ""))
        self.assertTrue(note, "the failure is in the chatter too")

    def test_missing_folder_logs_failure(self):
        config = self._config(folder="/nonexistent/drkds_backup_lite")
        with mute_logger(CONFIG_LOGGER):
            log = config._run_backup()
        self.assertEqual(log.status, "failed")
        self.assertIn("does not exist", log.message)
        self.assertEqual(len(self._todo_activities(config)), 2)

    def test_pg_dump_failure_is_logged_and_partial_file_removed(self):
        config = self._config(backup_format="dump")
        with patch(CONFIG_LOGGER + ".find_pg_tool", return_value="/bin/false"), \
                mute_logger(CONFIG_LOGGER):
            log = config._run_backup()
        self.assertEqual(log.status, "failed")
        self.assertIn("pg_dump exited with status 1", log.message)
        self.assertEqual(os.listdir(self.folder), [], "no .part file may survive")
        self.assertEqual(len(self._todo_activities(config)), 2)

    def test_no_notify_users_still_logs(self):
        config = self._config(notify_user_ids=[(5, 0, 0)])
        os.chmod(self.folder, stat.S_IRUSR | stat.S_IXUSR)
        with mute_logger(CONFIG_LOGGER):
            log = config._run_backup()
        self.assertEqual(log.status, "failed")
        self.assertFalse(self._todo_activities(config))

    def test_test_folder_button(self):
        config = self._config()
        ok = config.with_user(self.admin).action_test_folder()
        self.assertEqual(ok["params"]["type"], "success")
        self.assertIn(self.folder, ok["params"]["message"])
        self.assertEqual(os.listdir(self.folder), [], "the probe file is removed")

        os.chmod(self.folder, stat.S_IRUSR | stat.S_IXUSR)
        bad = config.with_user(self.admin).action_test_folder()
        self.assertEqual(bad["params"]["type"], "danger")
        self.assertIn("not writable", bad["params"]["message"])

        config.folder = "/nonexistent/drkds_backup_lite"
        missing = config.with_user(self.admin).action_test_folder()
        self.assertEqual(missing["params"]["type"], "danger")
        self.assertIn("does not exist", missing["params"]["message"])

    def test_folder_must_be_absolute(self):
        with self.assertRaises(ValidationError):
            self._config(folder="backups/relative")


@tagged("post_install", "-at_install")
class TestBackupSecurity(BackupCommon):
    def test_no_password_stored_anywhere(self):
        """The module keeps no credential: no field named like one, nothing in
        the parameters, and the database password, if the server uses one,
        appears neither in the log nor inside the archive."""
        for model in ("drkds.backup.lite.config", "drkds.backup.lite.log"):
            for fname in self.env[model]._fields:
                self.assertNotIn("passw", fname.lower(), "%s.%s" % (model, fname))
        params = self.env["ir.config_parameter"].sudo().search([("key", "like", "drkds_backup")])
        for param in params:
            self.assertNotIn("passw", param.key.lower())
            self.assertNotIn("passw", (param.value or "").lower())

        config = self._config()
        log = config._run_backup()
        self.assertEqual(log.status, "done", log.message)
        secret = tools.config["db_password"]
        with zipfile.ZipFile(log.path) as archive:
            manifest = archive.read("manifest.json").decode()
        self.assertNotIn("passw", manifest.lower())
        if secret:
            self.assertNotIn(secret, manifest)
            self.assertNotIn(secret, log.message or "")
            self.assertNotIn(secret, log.name)
        self.assertNotIn("passw", (log.message or "").lower())

    def test_cron_follows_the_configuration(self):
        config = self._config(interval_number=2, interval_type="hours")
        cron = config.cron_id
        self.assertTrue(cron)
        self.assertEqual(cron.interval_number, 2)
        self.assertEqual(cron.interval_type, "hours")
        self.assertEqual(cron.user_id, self.env.ref("base.user_root"))
        self.assertIn("model.browse(%d)._run_backup()" % config.id, cron.code)
        self.assertEqual(cron.model_id.model, "drkds.backup.lite.config")
        self.assertTrue(cron.active)

        config.write({"interval_number": 1, "interval_type": "days", "name": "Weekly"})
        self.assertEqual(cron.interval_number, 1)
        self.assertEqual(cron.interval_type, "days")
        self.assertEqual(cron.name, "Database backup: Weekly")

        config.active = False
        self.assertFalse(cron.active)
        config.active = True
        self.assertTrue(cron.active)

        with self.assertRaises(ValidationError):
            config.interval_number = 0

        cron_id = cron.id
        config.unlink()
        self.assertFalse(self.env["ir.cron"].browse(cron_id).exists())

    def test_copy_gets_its_own_cron(self):
        """The copy shares the folder, which two active configurations may
        not, so it starts archived with a paused schedule; given its own
        folder, it can be unarchived."""
        config = self._config()
        copy = config.copy()
        self.assertTrue(copy.cron_id)
        self.assertNotEqual(copy.cron_id, config.cron_id)
        self.assertEqual(copy.name, "Nightly (copy)")
        self.assertFalse(copy.active)
        self.assertFalse(copy.cron_id.active)
        with self.assertRaises(ValidationError):
            copy.active = True
        weekly = os.path.join(self.folder, "weekly")
        os.makedirs(weekly)
        copy.write({"folder": weekly, "active": True})
        self.assertTrue(copy.cron_id.active)

    def test_cron_run_writes_a_log(self):
        """What the scheduler executes: the server action code, as root."""
        config = self._config()
        config.cron_id.sudo().ir_actions_server_id.run()
        self.assertEqual(config.log_count, 1)
        self.assertEqual(config.last_status, "done", config.log_ids.message)

    def test_deleting_configuration_removes_its_logs(self):
        config = self._config()
        log = config._run_backup()
        config.unlink()
        self.assertFalse(log.exists())
