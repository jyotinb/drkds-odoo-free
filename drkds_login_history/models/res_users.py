# Part of the drkds free suite for Odoo 19 Community. See LICENSE (LGPL-3).
"""Hook the login path and expose per-user figures on the user form.

``res.users._login`` is the single place every interactive and RPC login
passes through, whatever the credential type, and it is where core itself
writes its "Login failed/successful" server log lines. Wrapping it records a
row on both outcomes and re-raises the failure unchanged, so the cooldown,
the error message and the rollback behave exactly as before.
"""

from datetime import datetime, time

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import AccessDenied


class ResUsers(models.Model):
    _inherit = "res.users"

    drkds_last_login_date = fields.Datetime(
        string="Last Successful Login",
        compute="_compute_drkds_login_stats",
        help="Date and time of the most recent successful login recorded.",
    )
    drkds_failed_today = fields.Integer(
        string="Failed Attempts Today",
        compute="_compute_drkds_login_stats",
        help="Failed login attempts recorded today, in your timezone.",
    )

    # ------------------------------------------------------------------
    # Authentication hook
    # ------------------------------------------------------------------

    def _login(self, credential, user_agent_env):
        login = credential.get("login") if isinstance(credential, dict) else None
        Record = self.env["drkds.login.record"]
        try:
            auth_info = super()._login(credential, user_agent_env=user_agent_env)
        except AccessDenied:
            Record._drkds_log_event("failed", login=login)
            raise
        Record._drkds_log_event("success", login=login, uid=auth_info.get("uid"))
        return auth_info

    # ------------------------------------------------------------------
    # Figures for the user form
    # ------------------------------------------------------------------

    @api.model
    def _drkds_today_start_utc(self):
        """Start of today in the current user's timezone, as naive UTC."""
        tz = pytz.timezone(self.env.user.tz or "UTC")
        now_local = fields.Datetime.now().replace(tzinfo=pytz.utc).astimezone(tz)
        start_local = tz.localize(datetime.combine(now_local.date(), time.min))
        return start_local.astimezone(pytz.utc).replace(tzinfo=None)

    @api.depends_context("uid")
    def _compute_drkds_login_stats(self):
        Record = self.env["drkds.login.record"].sudo()
        real = self.filtered(lambda user: isinstance(user.id, int))
        last_by_user = {}
        failed_by_user = {}
        if real:
            today_start = self._drkds_today_start_utc()
            for user, event_date in Record._read_group(
                [("user_id", "in", real.ids), ("result", "=", "success")],
                groupby=["user_id"],
                aggregates=["event_date:max"],
            ):
                last_by_user[user.id] = event_date
            for user, count in Record._read_group(
                [
                    ("user_id", "in", real.ids),
                    ("result", "=", "failed"),
                    ("event_date", ">=", today_start),
                ],
                groupby=["user_id"],
                aggregates=["__count"],
            ):
                failed_by_user[user.id] = count
        for user in self:
            user.drkds_last_login_date = last_by_user.get(user.id, False)
            user.drkds_failed_today = failed_by_user.get(user.id, 0)

    def action_drkds_open_login_history(self):
        """Smart button: this user's login history, newest first."""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "drkds_login_history.action_drkds_login_record"
        )
        action["domain"] = [("user_id", "=", self.id)]
        action["context"] = {"search_default_group_by_day": 0}
        action["display_name"] = _("Login History: %s", self.display_name)
        return action
