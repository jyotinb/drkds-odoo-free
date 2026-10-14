"""End to end: the administrator sets a default folder in Settings, creates a
nightly configuration through the form, checks the folder, runs it three
times with a retention of two, then watches a failure reach the watcher as a
to-do and the next run succeed again."""
import os
import stat
import zipfile

from odoo.tests import Form, tagged
from odoo.tools import mute_logger

from .common import CONFIG_LOGGER, BackupCommon


@tagged("post_install", "-at_install")
class TestBackupScenario(BackupCommon):
    def test_nightly_backup_week(self):
        admin_env = self.env(user=self.admin)

        # 1. Settings: a default folder for new configurations.
        settings = Form(admin_env["res.config.settings"])
        settings.drkds_backup_default_folder = self.folder
        settings.save().execute()
        self.assertEqual(
            self.env["ir.config_parameter"].sudo().get_param("drkds_backup_lite.default_folder"),
            self.folder,
        )

        # 2. The configuration, through the form: folder comes from Settings.
        f = Form(admin_env["drkds.backup.lite.config"])
        self.assertEqual(f.folder, self.folder)
        f.name = "Nightly"
        f.keep_last = 2
        f.notify_user_ids.add(self.watcher)
        config = f.save()
        self.assertEqual(config.backup_format, "zip")
        self.assertEqual(config.notify_user_ids, self.admin | self.watcher)
        self.assertTrue(config.cron_id.active)
        self.assertEqual(config.cron_id.interval_type, "days")

        # 3. Test folder says yes.
        self.assertEqual(config.action_test_folder()["params"]["type"], "success")

        # 4. Three nights with a retention of two: the first file goes.
        night1 = config._run_backup()
        night2 = config._run_backup()
        night3 = config._run_backup()
        self.assertEqual(night1.status, "deleted")
        self.assertEqual(night2.status, "done")
        self.assertEqual(night3.status, "done")
        self.assertEqual(self._backup_files(), [night2.name, night3.name])
        self.assertIn(night1.name, night3.message)
        self.assertEqual(config.log_count, 3)
        self.assertEqual(config.last_status, "done")
        with zipfile.ZipFile(night3.path) as archive:
            self.assertEqual(archive.namelist()[:2], ["dump.sql", "manifest.json"])

        # 5. The disk is mounted read-only one night: a failed run, a to-do
        #    for the admin and the watcher, nothing deleted.
        os.chmod(self.folder, stat.S_IRUSR | stat.S_IXUSR)
        with mute_logger(CONFIG_LOGGER):
            night4 = config._run_backup()
        self.assertEqual(night4.status, "failed")
        self.assertEqual(config.last_status, "failed")
        todos = self._todo_activities(config)
        self.assertEqual(todos.user_id, self.admin | self.watcher)
        self.assertEqual(self._backup_files(), [night2.name, night3.name])
        self.assertEqual(config.action_test_folder()["params"]["type"], "danger")

        # 6. Fixed: the next night succeeds and retention catches up.
        os.chmod(self.folder, stat.S_IRWXU)
        night5 = config._run_backup()
        self.assertEqual(night5.status, "done", night5.message)
        self.assertEqual(self._backup_files(), [night3.name, night5.name])
        self.assertEqual(night2.status, "deleted")
        self.assertEqual(config.log_count, 5)

        # 7. The admin clears the to-do; archiving pauses the schedule.
        todos.filtered(lambda a: a.user_id == self.admin).action_done()
        self.assertEqual(len(self._todo_activities(config)), 1)
        config.active = False
        self.assertFalse(config.cron_id.active)
