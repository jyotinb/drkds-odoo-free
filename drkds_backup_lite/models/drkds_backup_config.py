import json
import logging
import os
import re
import subprocess
import tempfile
import time
import zipfile
from datetime import datetime, timedelta

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.service.db import dump_db_manifest
from odoo.tools.misc import exec_pg_environ, find_pg_tool

_logger = logging.getLogger(__name__)

FORMATS = [
    ("zip", "Zip (SQL dump, manifest and filestore)"),
    ("dump", "PostgreSQL custom-format dump"),
]
EXTENSIONS = {"zip": "zip", "dump": "dump"}
INTERVAL_TYPES = [
    ("hours", "Hours"),
    ("days", "Days"),
    ("weeks", "Weeks"),
]


class DrkdsBackupConfig(models.Model):
    """One scheduled backup of the current database to one folder.

    Each configuration owns a scheduled action (``cron_id``) whose code calls
    :meth:`_run_backup` on it; the schedule fields on the form are the
    cron's own, so changing them on either side changes both. Archiving a
    configuration pauses its cron; deleting it deletes the cron.

    A run dumps the database with ``pg_dump`` using the connection settings
    Odoo itself runs with, so no master password is involved and none is
    kept. Core's :func:`odoo.service.db.dump_db` does the same work but is
    gated on ``list_db``, which a hardened server has turned off, so the
    dump is written here with the same helpers (``find_pg_tool``,
    ``exec_pg_environ``, ``dump_db_manifest``) and the same archive layout:
    ``dump.sql`` first, then ``manifest.json``, then ``filestore/``.

    Every run writes a :class:`drkds.backup.log` line. A failure never
    raises out of the cron: it is logged, posted to the chatter, and a to-do
    activity is scheduled for each notified user.
    """

    _name = "drkds.backup.config"
    _description = "Backup Configuration"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name, id"

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    folder = fields.Char(
        string="Backup Folder",
        required=True,
        tracking=True,
        default=lambda self: self._default_folder(),
        help="Absolute path of a folder on the Odoo server. It must exist and be "
             "writable by the system user that runs Odoo.",
    )
    backup_format = fields.Selection(
        FORMATS, string="Format", required=True, default="zip", tracking=True,
        help="Zip: dump.sql, manifest.json and the filestore, restorable from the "
             "database manager. Dump: pg_dump custom format, restorable with pg_restore.",
    )
    keep_last = fields.Integer(
        string="Keep Last", default=7, required=True, tracking=True,
        help="After a successful run, backups of this database older than the last N "
             "are removed from the folder. 0 keeps everything.",
    )
    notify_user_ids = fields.Many2many(
        "res.users",
        "drkds_backup_config_notify_rel",
        "config_id",
        "user_id",
        string="Notify on Failure",
        domain="[('share', '=', False)]",
        default=lambda self: self.env.user,
        help="Each of these users gets a to-do activity when a run fails.",
    )
    cron_id = fields.Many2one(
        "ir.cron", string="Scheduled Action", readonly=True, copy=False, ondelete="set null"
    )
    interval_number = fields.Integer(
        related="cron_id.interval_number", string="Every", readonly=False
    )
    interval_type = fields.Selection(
        related="cron_id.interval_type", string="Interval Unit", readonly=False
    )
    nextcall = fields.Datetime(related="cron_id.nextcall", string="Next Run", readonly=False)
    log_ids = fields.One2many("drkds.backup.log", "config_id", string="Runs")
    log_count = fields.Integer(compute="_compute_last_run")
    last_run = fields.Datetime(compute="_compute_last_run", string="Last Run")
    last_status = fields.Selection(
        [("done", "Done"), ("failed", "Failed"), ("deleted", "Done (file removed)")],
        compute="_compute_last_run", string="Last Status",
    )
    db_name = fields.Char(compute="_compute_db_name", string="Database")

    _keep_last_positive = models.Constraint(
        "check(keep_last >= 0)", "Keep Last cannot be negative."
    )

    # -- defaults and computes ------------------------------------------
    @api.model
    def _default_folder(self):
        return self.env["ir.config_parameter"].sudo().get_param(
            "drkds_backup_lite.default_folder", ""
        )

    def _compute_db_name(self):
        for config in self:
            config.db_name = self.env.cr.dbname

    @api.depends("log_ids.status", "log_ids.date_start")
    def _compute_last_run(self):
        for config in self:
            logs = config.log_ids.sorted(key=lambda l: (l.date_start, l.id), reverse=True)
            config.log_count = len(logs)
            config.last_run = logs[:1].date_start
            config.last_status = logs[:1].status

    @api.constrains("folder")
    def _check_folder_is_absolute(self):
        for config in self:
            if not os.path.isabs(config.folder.strip()):
                raise ValidationError(
                    _("The backup folder must be an absolute path, such as /var/backups/odoo.")
                )

    @api.constrains("interval_number")
    def _check_interval(self):
        for config in self:
            if config.cron_id and config.interval_number < 1:
                raise ValidationError(_("The interval must be at least 1."))

    # -- cron ownership -------------------------------------------------
    _CRON_FIELDS = ("interval_number", "interval_type", "nextcall")

    def _cron_values(self):
        self.ensure_one()
        return {
            "name": _("Database backup: %s", self.name),
            "model_id": self.env["ir.model"]._get_id(self._name),
            "state": "code",
            "code": "model.browse(%d)._run_backup()" % self.id,
            "user_id": self.env.ref("base.user_root").id,
            "active": self.active,
            "interval_number": 1,
            "interval_type": "days",
        }

    @api.model_create_multi
    def create(self, vals_list):
        # The schedule fields are related to a cron that does not exist yet.
        # A form sends them empty (0, False) when untouched; an empty value
        # means "the cron's default", so only filled values are carried over.
        schedules = []
        for vals in vals_list:
            schedule = {k: vals.pop(k) for k in self._CRON_FIELDS if k in vals}
            schedules.append({k: v for k, v in schedule.items() if v})
        configs = super().create(vals_list)
        for config, schedule in zip(configs, schedules):
            cron_vals = config._cron_values()
            cron_vals.update(schedule)
            cron = self.env["ir.cron"].sudo().create(cron_vals)
            config.cron_id = cron
        return configs

    def write(self, vals):
        result = super().write(vals)
        if "name" in vals or "active" in vals:
            for config in self.filtered("cron_id"):
                config.cron_id.sudo().write({
                    "name": _("Database backup: %s", config.name),
                    "active": config.active,
                })
        return result

    def unlink(self):
        crons = self.cron_id
        result = super().unlink()
        crons.sudo().unlink()
        return result

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if "name" not in default:
            for vals in vals_list:
                vals["name"] = _("%s (copy)", vals["name"])
        return vals_list

    # -- folder check ---------------------------------------------------
    def _check_folder(self):
        """Raise UserError if the Odoo system user cannot write to the folder.

        ``os.access`` is asked first, then a real file is created and
        removed, because access bits can say yes on a share that says no.
        """
        self.ensure_one()
        folder = self.folder.strip()
        if not os.path.isdir(folder):
            raise UserError(_("The folder %s does not exist on the Odoo server.", folder))
        if not os.access(folder, os.W_OK | os.X_OK):
            raise UserError(
                _("The folder %s is not writable by the system user running Odoo.", folder)
            )
        try:
            with tempfile.NamedTemporaryFile(dir=folder, prefix=".drkds_backup_probe_"):
                pass
        except OSError as exc:
            raise UserError(
                _("Could not create a file in %(folder)s: %(error)s",
                  folder=folder, error=exc)
            ) from exc

    def action_test_folder(self):
        """"Test folder" button: a green or red notification, nothing else."""
        self.ensure_one()
        try:
            self._check_folder()
        except UserError as exc:
            return self._notification(_("Folder check failed"), exc.args[0], "danger")
        return self._notification(
            _("Folder is writable"),
            _("Odoo can write backups to %s.", self.folder.strip()),
            "success",
        )

    def _notification(self, title, message, kind):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"title": title, "message": message, "type": kind, "sticky": False},
        }

    # -- the dump -------------------------------------------------------
    def _file_pattern(self):
        """Regex matching the files this module writes for this database."""
        return re.compile(
            r"^%s_\d{8}_\d{6}\.(zip|dump)$" % re.escape(self.env.cr.dbname)
        )

    def _pg_dump(self, extra_args):
        """Run pg_dump for the current database. Raise on a non-zero exit."""
        cmd = [find_pg_tool("pg_dump"), "--no-owner", *extra_args, self.env.cr.dbname]
        result = subprocess.run(
            cmd,
            env=exec_pg_environ(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "pg_dump exited with status %d: %s"
                % (result.returncode, (result.stderr or "").strip())
            )

    def _write_zip(self, part_path):
        """Write a zip restorable by the database manager to ``part_path``."""
        folder = os.path.dirname(part_path)
        with tempfile.TemporaryDirectory(dir=folder, prefix=".drkds_backup_tmp_") as tmp:
            sql_path = os.path.join(tmp, "dump.sql")
            self._pg_dump(["--file=" + sql_path])
            manifest = dump_db_manifest(self.env.cr)
            with zipfile.ZipFile(
                part_path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True
            ) as archive:
                archive.write(sql_path, "dump.sql")
                archive.writestr("manifest.json", json.dumps(manifest, indent=4))
                filestore = tools.config.filestore(self.env.cr.dbname)
                if os.path.isdir(filestore):
                    for dirpath, _dirnames, filenames in os.walk(filestore):
                        for filename in sorted(filenames):
                            full = os.path.join(dirpath, filename)
                            if os.path.isfile(full):
                                archive.write(
                                    full,
                                    os.path.join("filestore", os.path.relpath(full, filestore)),
                                )

    def _write_dump(self, part_path):
        self._pg_dump(["--format=c", "--file=" + part_path])

    def _run_backup(self):
        """Entry point of the cron and of the Backup Now button.

        Returns the log records written, one per configuration. Never
        raises for a failed dump; see the class docstring.
        """
        logs = self.env["drkds.backup.log"]
        for config in self:
            logs |= config._backup_once()
        return logs

    def _next_file_name(self, folder):
        """``<db>_<YYYYMMDD_HHMMSS>.<ext>``, UTC. Two runs inside the same
        second (a Backup Now right after the cron) must not overwrite each
        other, so the stamp is moved forward until the name is free."""
        self.ensure_one()
        when = datetime.utcnow().replace(microsecond=0)
        extension = EXTENSIONS[self.backup_format]
        while True:
            filename = "%s_%s.%s" % (
                self.env.cr.dbname, when.strftime("%Y%m%d_%H%M%S"), extension
            )
            final_path = os.path.join(folder, filename)
            if not os.path.exists(final_path):
                return filename, final_path
            when += timedelta(seconds=1)

    def _backup_once(self):
        self.ensure_one()
        started = time.monotonic()
        folder = self.folder.strip()
        filename, final_path = self._next_file_name(folder)
        part_path = final_path + ".part"
        log_vals = {
            "config_id": self.id,
            "name": filename,
            "folder": folder,
            "backup_format": self.backup_format,
            "date_start": fields.Datetime.now(),
        }
        try:
            self._check_folder()
            if self.backup_format == "zip":
                self._write_zip(part_path)
            else:
                self._write_dump(part_path)
            os.replace(part_path, final_path)
            log_vals.update({
                "status": "done",
                "size": os.path.getsize(final_path),
                "duration": time.monotonic() - started,
            })
        except Exception as exc:  # noqa: BLE001 - every cause must land in the log
            _logger.exception("Backup %s failed", self.name)
            if os.path.exists(part_path):
                try:
                    os.remove(part_path)
                except OSError:
                    _logger.warning("Could not remove partial backup %s", part_path)
            message = exc.args[0] if exc.args else str(exc)
            log_vals.update({
                "status": "failed",
                "duration": time.monotonic() - started,
                "message": str(message),
            })
        log = self.env["drkds.backup.log"].sudo().create(log_vals)
        if log.status == "done":
            removed = self._apply_retention()
            if removed:
                log.message = _("Removed by retention: %s", ", ".join(removed))
        else:
            self._notify_failure(log)
        return log

    def _apply_retention(self):
        """Delete this database's backup files beyond the last ``keep_last``.

        Only files named by this module for this database are considered, so
        anything else in the folder is left alone. Returns the names removed.
        """
        self.ensure_one()
        if self.keep_last <= 0:
            return []
        folder = self.folder.strip()
        pattern = self._file_pattern()
        names = sorted(
            (n for n in os.listdir(folder) if pattern.match(n)), reverse=True
        )
        removed = []
        for name in names[self.keep_last:]:
            try:
                os.remove(os.path.join(folder, name))
            except OSError as exc:
                _logger.warning("Retention could not remove %s: %s", name, exc)
                continue
            removed.append(name)
        if removed:
            self.env["drkds.backup.log"].sudo().search([
                ("folder", "=", folder),
                ("name", "in", removed),
                ("status", "=", "done"),
            ]).write({"status": "deleted"})
        return removed

    def _notify_failure(self, log):
        self.ensure_one()
        summary = _("Backup failed: %s", self.name)
        note = _(
            "The scheduled backup to %(folder)s failed at %(when)s.\n\n%(error)s",
            folder=log.folder, when=log.date_start, error=log.message or "",
        )
        self.message_post(body=note, message_type="comment", subtype_xmlid="mail.mt_note")
        for user in self.notify_user_ids:
            self.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=user.id,
                summary=summary,
                note=tools.html_escape(note).replace("\n", "<br/>"),
            )

    # -- buttons --------------------------------------------------------
    def action_backup_now(self):
        self.ensure_one()
        log = self._run_backup()
        return {
            "type": "ir.actions.act_window",
            "res_model": "drkds.backup.log",
            "res_id": log.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_logs(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "drkds_backup_lite.action_drkds_backup_log"
        )
        action["domain"] = [("config_id", "=", self.id)]
        action["context"] = {"default_config_id": self.id}
        return action
