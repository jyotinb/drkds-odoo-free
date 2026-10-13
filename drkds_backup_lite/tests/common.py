import os
import shutil
import stat
import tempfile

from odoo.tests import TransactionCase, new_test_user

#: The failure path logs with ``_logger.exception``; expected failures mute it.
CONFIG_LOGGER = "odoo.addons.drkds_backup_lite.models.drkds_backup_config"


class BackupCommon(TransactionCase):
    """A writable temporary folder per test, an administrator, a second
    administrator to be told about failures, and a plain employee who must
    not reach any of it. The folder is removed after each test, whatever its
    permissions were left at."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Config = cls.env["drkds.backup.config"]
        cls.Log = cls.env["drkds.backup.log"]
        cls.admin = new_test_user(
            cls.env, login="drkds_bkl_admin", name="Backup Admin",
            groups="base.group_user,base.group_system",
        )
        cls.watcher = new_test_user(
            cls.env, login="drkds_bkl_watcher", name="Backup Watcher",
            groups="base.group_user,base.group_system",
        )
        cls.employee = new_test_user(
            cls.env, login="drkds_bkl_employee", name="Plain Employee",
            groups="base.group_user",
        )

    def setUp(self):
        super().setUp()
        self.folder = tempfile.mkdtemp(prefix="drkds_bkl_")
        self.addCleanup(self._remove_folder)

    def _remove_folder(self):
        os.chmod(self.folder, stat.S_IRWXU)
        shutil.rmtree(self.folder, ignore_errors=True)

    def _config(self, **vals):
        values = {
            "name": "Nightly",
            "folder": self.folder,
            "backup_format": "zip",
            "keep_last": 3,
            "notify_user_ids": [(6, 0, (self.admin | self.watcher).ids)],
        }
        values.update(vals)
        return self.Config.with_user(self.admin).create(values)

    def _backup_files(self):
        pattern = self.Config._file_pattern()
        return sorted(n for n in os.listdir(self.folder) if pattern.match(n))

    def _todo_activities(self, config):
        return self.env["mail.activity"].search([
            ("res_model", "=", "drkds.backup.config"),
            ("res_id", "=", config.id),
        ])

    def _touch(self, name, content=b"old"):
        with open(os.path.join(self.folder, name), "wb") as fh:
            fh.write(content)
