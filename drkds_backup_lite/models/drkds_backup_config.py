import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
import zipfile
from datetime import datetime, timedelta

import odoo.addons
from odoo import _, api, fields, models, release, tools
from odoo.exceptions import AccessError, UserError, ValidationError
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
#: While a run works it writes ``<file>.part`` and, for a zip, keeps
#: ``dump.sql`` in a directory ``.<file>.tmp_<random>`` next to it. Both
#: carry the final file name, so the leftovers of a killed run can be found.
PART_SUFFIX = ".part"
TMP_INFIX = ".tmp_"


def _is_within(path, root):
    """Whether real path ``path`` is ``root`` or lies below it."""
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


class DrkdsBackupConfig(models.Model):
    """One scheduled backup of the current database to one folder.

    Each configuration owns a scheduled action (``cron_id``) whose code calls
    :meth:`_run_backup` on it; the schedule fields on the form are the
    cron's own, so changing them on either side changes both. Archiving a
    configuration pauses its cron; deleting it deletes the cron.

    A run dumps the database with ``pg_dump`` using the connection settings
    Odoo itself runs with, so no master password is involved and none is
    kept. Core's :func:`odoo.service.db.dump_db` does the same work but it,
    and ``dump_db_manifest`` with it, is gated on ``list_db``, which a
    hardened server has turned off. So the dump is written here with
    ``find_pg_tool`` and ``exec_pg_environ`` and the same archive layout:
    ``dump.sql`` first, then ``manifest.json``, then ``filestore/``.

    Every run writes a :class:`drkds.backup.lite.log` line, opened as "running".
    A failure never raises out of the cron: it is logged, posted to the
    chatter, and a to-do activity is scheduled for each notified user. A
    run whose worker is killed (``limit_time_real_cron``, a restart) is
    closed as failed by the next run; see :meth:`_close_interrupted_runs`.
    """

    _name = "drkds.backup.lite.config"
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
             "writable by the system user that runs Odoo, and may not be inside the "
             "filestore or an addons path. Each configuration needs its own folder.",
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
        "drkds_backup_lite_config_notify_rel",
        "config_id",
        "user_id",
        string="Notify on Failure",
        domain=lambda self: "[('share', '=', False), ('all_group_ids', 'in', [%d])]"
        % self.env.ref("base.group_system").id,
        default=lambda self: self.env.user,
        help="Administrators (Settings access) who get a to-do activity when a run fails.",
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
    log_ids = fields.One2many("drkds.backup.lite.log", "config_id", string="Runs")
    log_count = fields.Integer(compute="_compute_last_run")
    last_run = fields.Datetime(compute="_compute_last_run", string="Last Run")
    last_status = fields.Selection(
        [("running", "Running"), ("done", "Done"), ("failed", "Failed"),
         ("deleted", "Done (file removed)")],
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

    @api.constrains("folder", "active")
    def _check_folder_rules(self):
        for config in self:
            problem = config._folder_problem()
            if problem:
                raise ValidationError(problem)
            if config.active:
                other = config._folder_clash()
                if other:
                    raise ValidationError(config._clash_message(other))

    @api.constrains("interval_number")
    def _check_interval(self):
        for config in self:
            if config.cron_id and config.interval_number < 1:
                raise ValidationError(_("The interval must be at least 1."))

    @api.constrains("notify_user_ids")
    def _check_notify_users(self):
        for config in self:
            outsiders = config.notify_user_ids.filtered(
                lambda user: not user._has_group("base.group_system")
            )
            if outsiders:
                raise ValidationError(_(
                    "Only administrators (Settings access) can be notified, because the "
                    "to-do opens the backup configuration. Not administrators: %s.",
                    ", ".join(outsiders.mapped("name")),
                ))

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
        for vals in vals_list:
            if "name" not in default:
                vals["name"] = _("%s (copy)", vals["name"])
            if "folder" not in default and "active" not in default:
                # Two active configurations cannot share a folder (see
                # _folder_clash): the copy starts archived, to be given its
                # own folder and then unarchived.
                vals["active"] = False
        return vals_list

    # -- folder rules ---------------------------------------------------
    @api.model
    def _forbidden_folders(self):
        """``(real path, kind)`` of the places no backup folder may be in.

        The filestore (``kind`` "filestore"): a zip copies it, so a backup
        kept inside would copy the archive it is writing, which then grows
        until the disk is full. Every addons path ("addons"): Odoo serves the
        files of every module's ``static`` folder to anyone, without login.
        """
        places = [
            (os.path.join(tools.config["data_dir"], "filestore"), "filestore"),
            (tools.config.filestore(self.env.cr.dbname), "filestore"),
        ]
        places += [(path, "addons") for path in odoo.addons.__path__]
        return [(os.path.realpath(path), kind) for path, kind in places]

    def _folder_problem(self):
        """Why the folder cannot hold backups, or ``False``.

        Checked on save and again before every run, because a symlink that
        was harmless on save can be repointed afterwards.
        """
        self.ensure_one()
        folder = (self.folder or "").strip()
        if not os.path.isabs(folder):
            return _("The backup folder must be an absolute path, such as /var/backups/odoo.")
        if ".." in folder.replace(os.altsep or os.sep, os.sep).split(os.sep):
            return _("The backup folder may not contain '..'. Enter the folder it leads to.")
        real = os.path.realpath(folder)
        for root, kind in self._forbidden_folders():
            if not _is_within(real, root):
                continue
            if kind == "filestore":
                return _(
                    "%(folder)s is inside Odoo's filestore (%(root)s). A zip backup copies "
                    "the filestore, so it would copy its own backups, and the archive it is "
                    "writing, until the disk is full. Choose a folder outside it.",
                    folder=folder, root=root,
                )
            return _(
                "%(folder)s is inside the addons path %(root)s, whose module files Odoo "
                "serves to anyone on the web. Choose a folder outside every addons path.",
                folder=folder, root=root,
            )
        return False

    def _folder_clash(self):
        """Another active configuration of this database writing to the same
        real folder. Retention counts every backup file of this database in
        the folder, so the two would delete each other's copies."""
        self.ensure_one()
        real = os.path.realpath((self.folder or "").strip())
        others = self.search([("id", "!=", self.id)])
        return others.filtered(
            lambda other: os.path.realpath((other.folder or "").strip()) == real
        )[:1]

    def _clash_message(self, other):
        return _(
            "The configuration “%(other)s” already writes to %(folder)s. Retention keeps "
            "the last N backups of this database in a folder, so two configurations there "
            "would delete each other's copies. Give each configuration its own folder, "
            "for example a subfolder.",
            other=other.name, folder=other.folder,
        )

    def _check_folder(self):
        """Raise UserError if the folder may not or cannot receive backups.

        The folder rules come first (see :meth:`_folder_problem`). Then
        ``os.access`` is asked, and a real file is created and removed,
        because access bits can say yes on a share that says no.
        """
        self.ensure_one()
        problem = self._folder_problem()
        if problem:
            raise UserError(problem)
        other = self._folder_clash()
        if other:
            raise UserError(self._clash_message(other))
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
        self.check_access("read")
        try:
            self._check_folder()
        except AccessError:
            raise
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

    @api.model
    def _redact(self, text):
        """Hide the database password, should a tool ever print it."""
        secret = tools.config["db_password"]
        if secret and text:
            text = text.replace(secret, "********")
        return text

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
                % (result.returncode, self._redact((result.stderr or "").strip()))
            )

    def _dump_manifest(self):
        """The ``manifest.json`` the database manager puts in a zip.

        Built here because core's ``dump_db_manifest`` is gated on
        ``list_db`` and refuses to run on a server that hides its databases.
        """
        cr = self.env.cr
        cr.execute("SELECT name, latest_version FROM ir_module_module WHERE state = 'installed'")
        modules = dict(cr.fetchall())
        return {
            "odoo_dump": "1",
            "db_name": cr.dbname,
            "version": release.version,
            "version_info": release.version_info,
            "major_version": release.major_version,
            # read the way core reads it, e.g. 160015 gives "16.0"
            "pg_version": "%d.%d" % divmod(cr._cnx.server_version / 100, 100),
            "modules": modules,
        }

    def _write_zip(self, part_path):
        """Write a zip restorable by the database manager to ``part_path``."""
        folder = os.path.dirname(part_path)
        prefix = "." + os.path.basename(part_path)[: -len(PART_SUFFIX)] + TMP_INFIX
        own_output = os.path.realpath(folder)
        with tempfile.TemporaryDirectory(dir=folder, prefix=prefix) as tmp:
            sql_path = os.path.join(tmp, "dump.sql")
            self._pg_dump(["--file=" + sql_path])
            manifest = self._dump_manifest()
            with zipfile.ZipFile(
                part_path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True
            ) as archive:
                archive.write(sql_path, "dump.sql")
                archive.writestr("manifest.json", json.dumps(manifest, indent=4))
                filestore = tools.config.filestore(self.env.cr.dbname)
                if os.path.isdir(filestore):
                    for dirpath, dirnames, filenames in os.walk(filestore):
                        if _is_within(os.path.realpath(dirpath), own_output):
                            # Never archive our own output; _folder_problem
                            # already refuses such a folder, this is the guard.
                            dirnames[:] = []
                            continue
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
        logs = self.env["drkds.backup.lite.log"]
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

    def _is_scheduled_run(self):
        """Whether this call is the scheduler running this configuration's
        own scheduled action (also "Run Manually" from Scheduled Actions)."""
        ctx = self.env.context
        return bool(
            self.cron_id
            and ctx.get("cron_id") == self.cron_id.id
            and ctx.get("ir_cron_progress_id")
        )

    def _hold_schedule(self):
        """Backup Now: refuse while the scheduler runs this configuration,
        and keep the scheduler off it until this run's transaction ends.

        For the whole of a scheduled run the scheduler holds a row lock on
        the scheduled action and skips rows locked by others. Taking the
        same lock here keeps two runs of one configuration from dumping at
        once, and lets :meth:`_close_interrupted_runs` trust that no other
        run of it is alive.
        """
        cron = self.cron_id.sudo()
        if cron and not cron.try_lock_for_update(allow_referencing=True):
            raise UserError(_(
                "The backup “%s” is running right now. Its result appears under Runs "
                "when it ends.", self.name,
            ))

    def _remove_leftovers(self, folder, filename=None):
        """Delete the partial archive and the temporary dump directory of
        ``filename``, or of any backup file of this database when no name is
        given. Returns the names removed; a folder that cannot be listed
        gives an empty list."""
        if filename:
            base = re.escape(filename)
        else:
            base = r"%s_\d{8}_\d{6}\.(?:zip|dump)" % re.escape(self.env.cr.dbname)
        pattern = re.compile(r"^(?:%s%s|\.%s%s.+)$" % (
            base, re.escape(PART_SUFFIX), base, re.escape(TMP_INFIX),
        ))
        try:
            names = sorted(n for n in os.listdir(folder) if pattern.match(n))
        except OSError:
            return []
        removed = []
        for name in names:
            path = os.path.join(folder, name)
            try:
                if os.path.isdir(path) and not os.path.islink(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            except OSError as exc:
                _logger.warning("Could not remove partial backup %s: %s", path, exc)
                continue
            removed.append(name)
        return removed

    def _close_interrupted_runs(self):
        """Close what a killed run left behind: its "running" line and its
        partial files.

        A run that ends, well or badly, replaces "running" in the same
        transaction, and only a scheduled run makes the line visible before
        it ends (see :meth:`_backup_once`). The caller holds this
        configuration's scheduled action, as the scheduler or through
        :meth:`_hold_schedule`, so no other run of it is alive: any
        "running" line, and any partial file of this database in the
        folder, belongs to a run that died.
        """
        self.ensure_one()
        stale = self.env["drkds.backup.lite.log"].sudo().search(
            [("config_id", "=", self.id), ("status", "=", "running")]
        )
        for log in stale:
            removed = self._remove_leftovers(log.folder, log.name)
            _logger.warning("Backup %s: closing interrupted run %s", self.name, log.name)
            log.write({
                "status": "failed",
                "message": _(
                    "Interrupted: this run did not finish. The Odoo worker running it was "
                    "stopped, typically by the limit_time_real_cron time limit, a server "
                    "restart or a crash. Partial files removed: %s.",
                    ", ".join(removed) or _("none found"),
                ),
            })
            self._notify_failure(log)
        orphans = self._remove_leftovers(self.folder.strip())
        if orphans:
            _logger.warning(
                "Backup %s: removed partial files of an interrupted run: %s",
                self.name, ", ".join(orphans),
            )

    @api.model
    def _failure_message(self, exc):
        """The reason shown in the log, the chatter and the to-do."""
        if isinstance(exc, UserError):
            message = exc.args[0] if exc.args else str(exc)
        else:
            # str() keeps the text of an OSError ("[Errno 28] No space left
            # on device"); its first argument is only the number.
            message = str(exc) or exc.__class__.__name__
        return self._redact(message)

    def _backup_once(self):
        self.ensure_one()
        scheduled = self._is_scheduled_run()
        if not scheduled:
            self._hold_schedule()
        self._close_interrupted_runs()
        folder = self.folder.strip()
        filename, final_path = self._next_file_name(folder)
        part_path = final_path + PART_SUFFIX
        log = self.env["drkds.backup.lite.log"].sudo().create({
            "config_id": self.id,
            "name": filename,
            "folder": folder,
            "backup_format": self.backup_format,
            "date_start": fields.Datetime.now(),
            "status": "running",
        })
        if scheduled:
            # Commit the "running" line before the long part. If the worker
            # is killed (limit_time_real_cron, a restart), nothing after this
            # is kept and the next run closes this line as interrupted.
            self.env["ir.cron"]._commit_progress()
        started = time.monotonic()
        try:
            self._check_folder()
            if self.backup_format == "zip":
                self._write_zip(part_path)
            else:
                self._write_dump(part_path)
            os.replace(part_path, final_path)
            values = {"status": "done", "size": os.path.getsize(final_path)}
        except Exception as exc:  # noqa: BLE001 - every cause must land in the log
            _logger.exception("Backup %s failed", self.name)
            self._remove_leftovers(folder, filename)
            values = {"status": "failed", "message": self._failure_message(exc)}
        values["duration"] = time.monotonic() - started
        log.write(values)
        if log.status == "done":
            try:
                removed = self._apply_retention()
            except OSError as exc:
                _logger.warning("Retention of backup %s failed: %s", self.name, exc)
                log.message = _(
                    "The backup was written, but retention could not clean the folder: %s",
                    self._failure_message(exc),
                )
            else:
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
            self.env["drkds.backup.lite.log"].sudo().search([
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
        # Someone named while an administrator may have lost the right since.
        for user in self.notify_user_ids.filtered(
            lambda user: user._has_group("base.group_system")
        ):
            self.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=user.id,
                summary=summary,
                note=tools.html_escape(note).replace("\n", "<br/>"),
            )

    # -- buttons --------------------------------------------------------
    def action_backup_now(self):
        self.ensure_one()
        self.check_access("write")
        log = self._run_backup()
        return {
            "type": "ir.actions.act_window",
            "res_model": "drkds.backup.lite.log",
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
