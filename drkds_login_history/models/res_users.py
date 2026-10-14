# Part of the drkds free suite for Odoo 19 Community. See LICENSE (LGPL-3).
"""Hook the login path and expose per-user figures on the user form.

``res.users._login`` is the single place every interactive and RPC login
passes through, whatever the credential type, and it is where core itself
writes its "Login failed/successful" server log lines. Wrapping it records a
row on both outcomes and re-raises the failure unchanged, so the cooldown,
the error message and the rollback behave exactly as before.

Two-factor authentication splits a browser login in two requests. ``_login``
only checks the password; the session is signed in later, when the second
factor is accepted (``odoo.http.Session.finalize``). So a right password that
still waits for a code is recorded as *2FA Pending*, and the code check that
follows (``_check_credentials`` with the user's MFA credential type) records
its own *Success* or *Failed* row.
"""

from datetime import datetime, time

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import AccessDenied
from odoo.http import request

#: auth_totp's "remember this browser" cookie and the model behind it. Read
#: by name only: this module does not depend on auth_totp (auto-installed by
#: web) and must not import it. auth_totp_mail makes the same check at
#: authentication time to decide whether a login comes from a new device.
_TRUSTED_DEVICE_COOKIE = "td_id"
_TRUSTED_DEVICE_MODEL = "auth_totp.device"


def _typed_login(credential):
    """The login from a credential dict, whatever the credential type."""
    return credential.get("login") if isinstance(credential, dict) else None


class ResUsers(models.Model):
    _inherit = "res.users"

    drkds_last_login_date = fields.Datetime(
        string="Last Successful Login",
        compute="_compute_drkds_login_stats",
        groups="base.group_system",
        help="Date and time of the most recent successful login recorded.",
    )
    drkds_failed_today = fields.Integer(
        string="Failed Attempts Today",
        compute="_compute_drkds_login_stats",
        groups="base.group_system",
        help="Failed login attempts recorded today, in your timezone.",
    )

    # ------------------------------------------------------------------
    # Authentication hooks
    # ------------------------------------------------------------------

    def _login(self, credential, user_agent_env):
        Record = self.env["drkds.login.record"]
        try:
            auth_info = super()._login(credential, user_agent_env=user_agent_env)
        except AccessDenied:
            # Read the login only now: auth_passkey fills it in place from the
            # passkey before its super() call, below this override.
            Record._drkds_log_event("failed", login=_typed_login(credential))
            raise
        result = "mfa_pending" if self._drkds_mfa_pending(auth_info, user_agent_env) else "success"
        Record._drkds_log_event(
            result, login=_typed_login(credential), uid=auth_info.get("uid")
        )
        return auth_info

    @api.model
    def _drkds_mfa_pending(self, auth_info, user_agent_env):
        """Whether this login still has to pass a second factor.

        Mirrors ``odoo.http.Session.authenticate``, which signs the session in
        at once unless the login is interactive, the credential does not skip
        MFA (a passkey does) and the user has an MFA step; and auth_totp's
        ``/web/login/totp``, which skips the code for a remembered browser.
        RPC logins (``interactive`` False) never get a second step.
        """
        if not (user_agent_env or {}).get("interactive") or auth_info.get("mfa") == "skip":
            return False
        uid = auth_info.get("uid")
        if not uid or not self.browse(uid)._mfa_url():
            return False
        return not self._drkds_trusted_device(uid)

    @api.model
    def _drkds_trusted_device(self, uid):
        """Whether the request carries a valid "remember this browser" key."""
        if not request or _TRUSTED_DEVICE_MODEL not in self.env:
            return False
        key = request.cookies.get(_TRUSTED_DEVICE_COOKIE)
        return bool(key) and bool(
            self.env[_TRUSTED_DEVICE_MODEL]._check_credentials_for_uid(
                scope="browser", key=key, uid=uid
            )
        )

    def _drkds_is_second_factor(self, credential):
        """Whether this credential check is the second step of a login.

        True only while the session waits for this very user's second factor
        (``pre_uid`` set, nobody signed in) and the credential is of the
        user's MFA type. A password check inside ``_login``, an identity
        check of a signed-in user and every RPC call are left alone.
        """
        if not request or len(self) != 1 or not isinstance(credential, dict):
            return False
        session = request.session
        if session.uid or session.get("pre_uid") != self.id:
            return False
        mfa_type = self._mfa_type()
        return bool(mfa_type) and credential.get("type") == mfa_type

    def _check_credentials(self, credential, env):
        second_factor = self._drkds_is_second_factor(credential)
        if not second_factor:
            return super()._check_credentials(credential, env)
        Record = self.env["drkds.login.record"]
        login = request.session.get("pre_login") or self.sudo().login
        try:
            auth_info = super()._check_credentials(credential, env)
        except AccessDenied:
            Record._drkds_log_event("failed", login=login, uid=self.id)
            raise
        Record._drkds_log_event("success", login=login, uid=self.id)
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

    def action_drkds_open_failed_today(self):
        """Smart button: the failed attempts the "Failed Today" figure counts.

        The search view's Failed and Today filters select exactly those rows:
        "today" is resolved by the server in the user's timezone, as the
        figure is.
        """
        action = self.action_drkds_open_login_history()
        action["context"] = {"search_default_failed": 1, "search_default_today": 1}
        return action
