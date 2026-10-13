import os

from odoo import api, fields, models

STATUSES = [
    ("running", "Running"),
    ("done", "Done"),
    ("failed", "Failed"),
    ("deleted", "Done (file removed)"),
]


class DrkdsBackupLog(models.Model):
    """One line per backup run: what was written, where, how big, how long.

    Written by :meth:`drkds.backup.config._backup_once`, in sudo, and never
    edited by hand (nobody has write access). A line opens as ``running`` and
    ends as ``done`` or ``failed``; a scheduled run killed on the way is
    closed as ``failed`` by the next run. The only later change is ``status``
    moving to ``deleted`` when retention removes the file.
    """

    _name = "drkds.backup.log"
    _description = "Backup Run"
    _order = "date_start desc, id desc"
    _rec_name = "name"

    config_id = fields.Many2one(
        "drkds.backup.config", string="Configuration", required=True,
        ondelete="cascade", index=True,
    )
    name = fields.Char(string="File", required=True, readonly=True)
    folder = fields.Char(required=True, readonly=True)
    path = fields.Char(compute="_compute_path", string="Full Path")
    backup_format = fields.Selection(
        [("zip", "Zip"), ("dump", "Dump")], string="Format", readonly=True
    )
    date_start = fields.Datetime(string="Started", required=True, readonly=True)
    duration = fields.Float(string="Duration (s)", readonly=True, digits=(16, 1))
    # Float, not Integer: an integer column overflows past 2 GiB.
    size = fields.Float(string="Size (bytes)", readonly=True, digits=(20, 0))
    size_display = fields.Char(compute="_compute_size_display", string="Size")
    status = fields.Selection(STATUSES, required=True, readonly=True, index=True)
    message = fields.Text(readonly=True)
    file_exists = fields.Boolean(compute="_compute_file_exists", string="File Present")

    @api.depends("folder", "name")
    def _compute_path(self):
        for log in self:
            log.path = os.path.join(log.folder or "", log.name or "")

    @api.depends("size")
    def _compute_size_display(self):
        for log in self:
            size = float(log.size or 0)
            unit = "B"
            for candidate in ("KB", "MB", "GB", "TB"):
                if size < 1024:
                    break
                size /= 1024.0
                unit = candidate
            log.size_display = ("%d %s" if unit == "B" else "%.1f %s") % (size, unit)

    @api.depends("folder", "name", "status")
    def _compute_file_exists(self):
        for log in self:
            log.file_exists = log.status != "failed" and os.path.isfile(log.path)
