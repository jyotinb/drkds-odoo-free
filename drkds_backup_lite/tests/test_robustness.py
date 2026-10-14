"""What goes wrong on a real server: a database past 2 GiB, a hardened
configuration, a full disk, a careless folder, two configurations side by
side, a worker killed mid-dump, and who may see or change what."""
import json
import os
import shutil
import stat
import tempfile
import zipfile
from unittest.mock import patch

from odoo import tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.service.db import dump_db_manifest
from odoo.tests import Form, tagged
from odoo.tools import mute_logger

from .common import CONFIG_LOGGER, BackupCommon

MODULE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class OptionMixin:
    def _set_option(self, key, value):
        old = tools.config[key]
        tools.config[key] = value
        self.addCleanup(tools.config.__setitem__, key, old)


@tagged("post_install", "-at_install")
class TestBackupServerConditions(OptionMixin, BackupCommon):
    def test_zip_backup_works_with_database_listing_disabled(self):
        """A hardened server sets list_db = False, which makes core's dump
        helpers refuse to run. The zip, manifest included, must still be
        written."""
        self._set_option("list_db", False)
        config = self._config()
        log = config._run_backup()
        self.assertEqual(log.status, "done", log.message)
        with zipfile.ZipFile(log.path) as archive:
            manifest = json.loads(archive.read("manifest.json"))
        self.assertEqual(manifest["odoo_dump"], "1")
        self.assertEqual(manifest["db_name"], self.env.cr.dbname)
        self.assertIn("drkds_backup_lite", manifest["modules"])

    def test_manifest_is_the_one_the_database_manager_writes(self):
        self._set_option("list_db", True)
        self.assertEqual(self.Config._dump_manifest(), dump_db_manifest(self.env.cr))

    def test_size_above_two_gib(self):
        """3 GiB is 3 * 1024**3 = 3,221,225,472 bytes, past the largest value
        of a 32-bit integer column (2,147,483,647)."""
        config = self._config()
        real_getsize = os.path.getsize
        with patch(CONFIG_LOGGER + ".os.path.getsize",
                   side_effect=lambda p: 3 * 1024 ** 3 if p.endswith(".zip") else real_getsize(p)):
            log = config._run_backup()
        self.assertEqual(log.status, "done", log.message)
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(log.size, 3221225472)
        self.assertEqual(log.size_display, "3.0 GB")

    def test_disk_full_mid_write(self):
        """The archive is written to /dev/full, which answers every write
        with ENOSPC: the run fails with a readable reason, and neither the
        partial archive nor the temporary dump is left behind."""
        if not os.path.exists("/dev/full"):
            self.skipTest("needs /dev/full")
        config = self._config()
        name, final = config._next_file_name(self.folder)

        def name_on_a_full_disk(folder):
            os.symlink("/dev/full", final + ".part")
            return name, final

        with patch.object(type(config), "_next_file_name", side_effect=name_on_a_full_disk), \
                mute_logger(CONFIG_LOGGER):
            log = config._run_backup()
        self.assertEqual(log.status, "failed")
        self.assertIn("No space left on device", log.message)
        self.assertEqual(os.listdir(self.folder), [])
        self.assertEqual(len(self._todo_activities(config)), 2)

    def test_failure_text_never_carries_the_database_password(self):
        secret = "Rv7-s3cret-pass"
        self._set_option("db_password", secret)
        bindir = tempfile.mkdtemp(prefix="drkds_bkl_bin_")
        self.addCleanup(shutil.rmtree, bindir, True)
        fake = os.path.join(bindir, "pg_dump")
        with open(fake, "w") as fh:
            fh.write('#!/bin/sh\necho "pg_dump: error: login refused ($PGPASSWORD)" >&2\nexit 1\n')
        os.chmod(fake, stat.S_IRWXU)
        config = self._config(backup_format="dump")
        with patch(CONFIG_LOGGER + ".find_pg_tool", return_value=fake), \
                mute_logger(CONFIG_LOGGER):
            log = config._run_backup()
        self.assertEqual(log.status, "failed")
        self.assertIn("login refused (********)", log.message)
        self.assertNotIn(secret, log.message)
        for activity in self._todo_activities(config):
            self.assertNotIn(secret, activity.note)
        for message in config.message_ids:
            self.assertNotIn(secret, message.body or "")

    def test_retention_that_cannot_list_the_folder_keeps_the_run(self):
        """A folder Odoo may write into but not list (mode -wx): the backup
        is written and kept, and the log says retention could not run."""
        if os.geteuid() == 0:
            self.skipTest("root can list any folder")
        config = self._config(keep_last=1)
        os.chmod(self.folder, stat.S_IWUSR | stat.S_IXUSR)
        with mute_logger(CONFIG_LOGGER):
            log = config._run_backup()
        os.chmod(self.folder, stat.S_IRWXU)
        self.assertEqual(log.status, "done")
        self.assertIn("retention could not", log.message)
        self.assertEqual(self._backup_files(), [log.name])
        self.assertFalse(self._todo_activities(config))


@tagged("post_install", "-at_install")
class TestBackupFolderRules(BackupCommon):
    def _filestore_root(self):
        return os.path.join(tools.config["data_dir"], "filestore")

    def test_folder_inside_the_filestore_is_refused(self):
        own = tools.config.filestore(self.env.cr.dbname)
        for folder in (own, own + "/backups", self._filestore_root()):
            with self.subTest(folder=folder), self.assertRaises(ValidationError):
                self._config(folder=folder)

    def test_folder_inside_an_addons_path_is_refused(self):
        """Every file under a module's static/ is served to anyone."""
        for folder in (os.path.join(MODULE_DIR, "static", "backups"),
                       os.path.dirname(MODULE_DIR)):
            with self.subTest(folder=folder), self.assertRaises(ValidationError):
                self._config(folder=folder)

    def test_dotdot_is_refused(self):
        with self.assertRaises(ValidationError):
            self._config(folder=self.folder + "/../" + os.path.basename(self.folder))

    def test_symlink_is_judged_by_where_it_leads(self):
        into_filestore = os.path.join(self.folder, "fs")
        os.symlink(self._filestore_root(), into_filestore)
        with self.assertRaises(ValidationError):
            self._config(folder=into_filestore)

        elsewhere = tempfile.mkdtemp(prefix="drkds_bkl_target_")
        self.addCleanup(shutil.rmtree, elsewhere, True)
        link = os.path.join(self.folder, "nas")
        os.symlink(elsewhere, link)
        log = self._config(folder=link)._run_backup()
        self.assertEqual(log.status, "done", log.message)
        self.assertEqual(os.listdir(elsewhere), [log.name])

    def test_folder_repointed_into_the_filestore_fails_the_run(self):
        """A symlink accepted on save can be repointed later. The run checks
        again and writes nothing; the zip must never archive its own output,
        which would grow until the disk is full."""
        fake_filestore = os.path.join(self.folder, "filestore")
        trap = os.path.join(fake_filestore, "backups")
        os.makedirs(trap)
        self._touch(os.path.join("filestore", "attachment.bin"), b"x" * 1000)
        safe = os.path.join(self.folder, "safe")
        os.makedirs(safe)
        link = os.path.join(self.folder, "target")
        os.symlink(safe, link)
        config = self._config(folder=link)
        os.remove(link)
        os.symlink(trap, link)

        real_write = zipfile.ZipFile.write

        def guarded_write(archive, filename, *args, **kwargs):
            if os.path.realpath(filename).startswith(trap + os.sep):
                raise AssertionError("the zip archived its own output: %s" % filename)
            return real_write(archive, filename, *args, **kwargs)

        with patch.object(type(tools.config), "filestore", lambda _config, _db: fake_filestore), \
                patch.object(zipfile.ZipFile, "write", guarded_write), \
                mute_logger(CONFIG_LOGGER):
            log = config._run_backup()
        self.assertEqual(log.status, "failed")
        self.assertIn("inside Odoo's filestore", log.message)
        self.assertEqual(os.listdir(trap), [])

    def test_two_configurations_cannot_share_a_folder(self):
        """Retention counts every backup file of this database in the
        folder, so a second configuration there would have its copies
        deleted by the first one's retention."""
        first = self._config(name="Nightly zip")
        for folder in (self.folder, self.folder + "/"):
            with self.subTest(folder=folder), self.assertRaises(ValidationError):
                self._config(name="Weekly dump", backup_format="dump", folder=folder)
        link = os.path.join(tempfile.mkdtemp(prefix="drkds_bkl_link_"), "same")
        self.addCleanup(shutil.rmtree, os.path.dirname(link), True)
        os.symlink(self.folder, link)
        with self.assertRaises(ValidationError):
            self._config(name="Through a link", folder=link)

        weekly_folder = os.path.join(self.folder, "weekly")
        os.makedirs(weekly_folder)
        weekly = self._config(name="Weekly dump", backup_format="dump", folder=weekly_folder)
        self.assertTrue(weekly)

        first.active = False
        replacement = self._config(name="Replacement")
        self.assertTrue(replacement, "an archived configuration does not hold its folder")
        with self.assertRaises(ValidationError):
            first.active = True


@tagged("post_install", "-at_install")
class TestBackupInterrupted(BackupCommon):
    def test_killed_scheduled_run_is_closed_by_the_next_run(self):
        """A scheduled run commits its "running" line before the dump. When
        limit_time_real_cron kills the worker, that line and the partial
        files stay. The next run closes the line as failed, removes this
        database's partial files (a killed Backup Now leaves files without a
        line) and tells the notified users."""
        config = self._config(keep_last=0)
        db = self.env.cr.dbname
        dead_name = "%s_20261012_020000.zip" % db
        dead = self.Log.create({
            "config_id": config.id, "name": dead_name, "folder": self.folder,
            "backup_format": "zip", "status": "running", "date_start": "2026-10-12 02:00:00",
        })
        self._touch(dead_name + ".part", b"half an archive")
        tmp = os.path.join(self.folder, ".%s.tmp_k1ll3d" % dead_name)
        os.makedirs(tmp)
        with open(os.path.join(tmp, "dump.sql"), "wb") as fh:
            fh.write(b"-- half a dump")
        orphan = "%s_20261011_020000.dump.part" % db
        self._touch(orphan)
        foreign = "other_db_20261012_020000.zip.part"
        self._touch(foreign)

        with mute_logger(CONFIG_LOGGER):
            log = config._run_backup()

        self.assertEqual(log.status, "done", log.message)
        self.assertEqual(dead.status, "failed")
        self.assertIn("Interrupted", dead.message)
        self.assertIn(dead_name + ".part", dead.message)
        self.assertEqual(sorted(os.listdir(self.folder)), sorted([log.name, foreign]))
        activities = self._todo_activities(config)
        self.assertEqual(activities.user_id, self.admin | self.watcher)
        self.assertIn("Interrupted", activities[0].note)
        self.assertEqual(config.log_count, 2)
        self.assertEqual(config.last_status, "done")

    def test_scheduled_run_makes_its_running_line_durable(self):
        """Inside the scheduler the line is committed, through the cron
        progress API, while it still says "running"; the scheduler already
        holds the scheduled action, so the run does not try to lock it."""
        config = self._config()
        cron = config.cron_id
        progress = self.env["ir.cron.progress"].create({"cron_id": cron.id})
        seen = []

        def commit_progress(_crons, *args, **kwargs):
            seen.append(self.Log.search([("config_id", "=", config.id)]).mapped("status"))
            return float("inf")

        IrCron = type(self.env["ir.cron"])
        with patch.object(IrCron, "_commit_progress", commit_progress), \
                patch.object(IrCron, "try_lock_for_update",
                             side_effect=AssertionError("the scheduler holds this lock")):
            log = config.with_context(cron_id=cron.id, ir_cron_progress_id=progress.id)._run_backup()
        self.assertEqual(seen, [["running"]])
        self.assertEqual(log.status, "done", log.message)

    def test_backup_now_refused_while_the_scheduler_runs_it(self):
        config = self._config()
        IrCron = type(self.env["ir.cron"])
        with patch.object(IrCron, "try_lock_for_update", lambda crons, **kw: crons.browse()), \
                self.assertRaises(UserError) as caught:
            config.with_user(self.admin).action_backup_now()
        self.assertIn("running right now", str(caught.exception))
        self.assertFalse(config.log_ids)
        self.assertEqual(os.listdir(self.folder), [])


@tagged("post_install", "-at_install")
class TestBackupAccess(BackupCommon):
    def test_only_administrators_can_be_notified(self):
        """A plain employee cannot open the configuration their to-do would
        point at, so they cannot be named."""
        with self.assertRaises(ValidationError):
            self._config(notify_user_ids=[(6, 0, (self.admin | self.employee).ids)])

    def test_notified_user_who_lost_admin_rights_gets_no_todo(self):
        config = self._config()
        self.watcher.write({"group_ids": [(3, self.env.ref("base.group_system").id)]})
        os.chmod(self.folder, stat.S_IRUSR | stat.S_IXUSR)
        with mute_logger(CONFIG_LOGGER):
            log = config._run_backup()
        self.assertEqual(log.status, "failed")
        self.assertEqual(self._todo_activities(config).user_id, self.admin)

    def test_buttons_do_not_hide_an_access_error(self):
        config = self._config()
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            config.with_user(self.employee).action_test_folder()
        with self.assertRaises(AccessError):
            config.with_user(self.employee).action_backup_now()
        self.assertFalse(config.log_ids)

    def test_run_log_cannot_be_rewritten(self):
        """The log is the record of what happened: even an administrator
        cannot rewrite a status or a message through the ORM or RPC, only
        delete old lines."""
        log = self._config()._run_backup()
        self.env.invalidate_all()
        with self.assertRaises(AccessError):
            log.with_user(self.admin).write({"status": "failed", "message": "edited"})
        log.with_user(self.admin).unlink()
        self.assertFalse(log.exists())


@tagged("post_install", "-at_install")
class TestBackupModelNames(BackupCommon):
    """The models are this module's own, so it can be installed next to the
    drkds Backup app.

    They used to be named drkds.backup.config and drkds.backup.log, which
    drkds_backup_manager also defines. With both installed, Odoo kept only
    the later definition under each name: the two modules shared one table,
    this module's fields (folder, keep_last, cron_id) left the registry and
    every one of its screens failed to load. Run this suite on a database
    where both modules are installed to prove they coexist.
    """

    def test_models_are_not_shared_with_another_module(self):
        for model in (self.Config, self.Log):
            self.assertNotIn(model._name, ("drkds.backup.config", "drkds.backup.log"))
            self.assertEqual(
                self.env["ir.model"]._get(model._name).modules, "drkds_backup_lite",
                "%s is also defined by another module" % model._name,
            )
        for fname in ("folder", "keep_last", "cron_id", "nextcall"):
            self.assertIn(fname, self.Config._fields)
        for fname in ("folder", "path", "file_exists"):
            self.assertIn(fname, self.Log._fields)

    def test_views_match_the_registered_models(self):
        views = self.env["ir.ui.view"].browse(self.env["ir.model.data"].search([
            ("module", "=", "drkds_backup_lite"), ("model", "=", "ir.ui.view"),
        ]).mapped("res_id"))
        self.assertEqual(len(views), 7)
        for view in views:
            view._check_xml()
        f = Form(self.Config.with_user(self.admin))
        f.name = "Nightly"
        f.folder = self.folder
        self.assertTrue(f.save().cron_id)
