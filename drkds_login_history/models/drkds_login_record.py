# Part of the drkds free suite for Odoo 19 Community. See LICENSE (LGPL-3).
"""The login audit table and the detached writer that fills it.

Odoo's own ``res.device.log`` remembers the devices behind sessions that
succeeded. It never sees the attempt that failed, the login name that was
typed, or the moment a user signed out. This model keeps one row per event,
success, failure or logout, so an administrator can answer "who tried to get
in, from where, and when".

Writing the row is the delicate part. A failed login raises
``AccessDenied`` and Odoo rolls the request back, which would silently drop a
row written in that same transaction. So every event is written through a
cursor of its own and committed at once (:meth:`_drkds_write_detached`). That
writer must also never stop a login: if the table is missing or unwritable,
the event goes to the server log and the authentication carries on.
"""

import hashlib
import logging
from datetime import timedelta

from odoo import SUPERUSER_ID, api, fields, models
from odoo.http import request

_logger = logging.getLogger(__name__)

PURGE_DAYS_PARAM = "drkds_login_history.purge_days"
PURGE_DAYS_DEFAULT = 180

#: Longest text kept per column. Every value below comes from the client
#: (the typed login, the User-Agent header, and with proxy mode the
#: X-Forwarded-For header), unauthenticated, so an attacker could otherwise
#: write tens of kilobytes per failed attempt. Real values are far shorter.
LOGIN_SIZE = 255
USER_AGENT_SIZE = 1024
IP_SIZE = 64


def _clip(value, size):
    """``value`` as text, cut to ``size`` characters; ``False`` when empty.

    RPC callers can send any JSON or XML-RPC type as the login, so a value is
    turned into text rather than assumed to be a string.
    """
    if value is None or value is False:
        return False
    text = value if isinstance(value, str) else str(value)
    return text[:size] or False


#: Ordered (needle, label) pairs. The first match wins, so the specific
#: tokens come before the generic ones: Edge and Opera both announce Chrome,
#: and nearly every browser announces Safari.
_BROWSER_RULES = (
    ("edg/", "Edge"),
    ("edge/", "Edge"),
    ("edga/", "Edge"),
    ("edgios/", "Edge"),
    ("opr/", "Opera"),
    ("opera", "Opera"),
    ("samsungbrowser/", "Samsung Internet"),
    ("fxios/", "Firefox"),
    ("firefox/", "Firefox"),
    ("crios/", "Chrome"),
    ("chromium/", "Chromium"),
    ("chrome/", "Chrome"),
    ("safari/", "Safari"),
    ("trident/", "Internet Explorer"),
    ("msie", "Internet Explorer"),
)

_OS_RULES = (
    ("windows phone", "Windows Phone"),
    ("windows", "Windows"),
    ("iphone", "iOS"),
    ("ipad", "iOS"),
    ("ipod", "iOS"),
    ("android", "Android"),
    ("cros", "ChromeOS"),
    ("mac os x", "macOS"),
    ("macintosh", "macOS"),
    ("linux", "Linux"),
    ("freebsd", "FreeBSD"),
)


def parse_user_agent(user_agent):
    """Return ``(browser, os)`` labels for a user agent string.

    Deliberately small: it recognises the common desktop and mobile browsers
    and operating systems by their well-known tokens and says "Other" for the
    rest. Anything smarter needs a maintained signature database, which would
    be an external dependency this module does not want.
    """
    text = (user_agent or "").lower()
    if not text.strip():
        return ("Unknown", "Unknown")
    browser = next((label for needle, label in _BROWSER_RULES if needle in text), "Other")
    os_name = next((label for needle, label in _OS_RULES if needle in text), "Other")
    return (browser, os_name)


class DrkdsLoginRecord(models.Model):
    """One authentication event: a success, a failure or a logout."""

    _name = "drkds.login.record"
    _description = "Login History Record"
    _order = "event_date desc, id desc"
    _rec_name = "login"

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="User",
        ondelete="set null",
        index=True,
        help="The user whose login name was used. Empty when the login name "
        "matched no user at all.",
    )
    login = fields.Char(
        string="Login Typed",
        index=True,
        help="The login name exactly as it was typed, whether or not it exists.",
    )
    event_date = fields.Datetime(
        string="Date",
        required=True,
        default=fields.Datetime.now,
        index=True,
    )
    result = fields.Selection(
        selection=[
            ("success", "Success"),
            ("mfa_pending", "2FA Pending"),
            ("failed", "Failed"),
            ("logout", "Logout"),
        ],
        string="Result",
        required=True,
        index=True,
        help="Success: the user is signed in. 2FA Pending: the password was "
        "right and Odoo asked for the second factor; the outcome of that step "
        "follows as its own Success or Failed row. Failed: wrong login, "
        "password or code, or a refused attempt. Logout: the session was ended.",
    )
    ip_address = fields.Char(string="IP Address")
    user_agent = fields.Text(string="User Agent")
    browser = fields.Char(string="Browser")
    os_name = fields.Char(string="Operating System")
    session_hash = fields.Char(
        string="Session Hash",
        size=64,
        help="SHA-256 of the session identifier. The identifier itself is "
        "never stored; the hash only tells two events of one session apart.",
    )
    country_name = fields.Char(
        string="Country",
        help="Always empty. No geolocation lookup is made because this module "
        "makes no outbound network call.",
    )

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    @api.model
    def _drkds_request_values(self):
        """Values read from the current HTTP request, or blanks without one."""
        if not request:
            return {}
        httprequest = request.httprequest
        user_agent = _clip(httprequest.environ.get("HTTP_USER_AGENT"), USER_AGENT_SIZE)
        browser, os_name = parse_user_agent(user_agent)
        session = getattr(request, "session", None)
        sid = getattr(session, "sid", None) if session is not None else None
        return {
            "ip_address": _clip(httprequest.remote_addr, IP_SIZE),
            "user_agent": user_agent,
            "browser": browser,
            "os_name": os_name,
            "session_hash": hashlib.sha256(sid.encode()).hexdigest() if sid else False,
        }

    @api.model
    def _drkds_log_event(self, result, login=None, uid=None):
        """Record one event. Never raises; see :meth:`_drkds_write_detached`.

        The values are gathered inside the guard too: they come from the
        client, and a malformed one must cost the audit row, not the login.
        """
        try:
            values = {
                "result": result,
                "login": _clip(login, LOGIN_SIZE),
                "user_id": uid or False,
                "event_date": fields.Datetime.now(),
                **self._drkds_request_values(),
            }
        except Exception:  # noqa: BLE001 - deliberately broad, see docstring
            _logger.warning(
                "drkds_login_history: could not prepare %s event", result, exc_info=True
            )
            return False
        return self._drkds_write_detached(values)

    @api.model
    def _drkds_write_detached(self, values):
        """Insert ``values`` through a separate cursor and commit immediately.

        The caller's transaction is left untouched, so the row survives the
        rollback that follows a failed login. The user is resolved here, from
        the typed login, when the caller could not provide it (a failure).
        Archived users are included: Odoo refuses their login, but an attempt
        on a deactivated account is exactly what an administrator must see
        against that account rather than as an unknown name.

        Returns the new record id, or ``False`` when nothing could be written.
        Every failure is logged and swallowed: an audit row is never worth a
        blocked login, and the table may legitimately be gone while the module
        is being uninstalled.
        """
        registry = self.pool
        if self._name not in registry:
            return False
        try:
            with registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                if not values.get("user_id") and values.get("login"):
                    Users = env["res.users"].with_context(active_test=False)
                    user = Users.search(
                        Users._get_login_domain(values["login"]),
                        order="active desc, %s" % Users._get_login_order(),
                        limit=1,
                    )
                    values["user_id"] = user.id or False
                record = env[self._name].create(values)
                return record.id
        except Exception:  # noqa: BLE001 - deliberately broad, see docstring
            _logger.warning(
                "drkds_login_history: could not record %s event for login %r",
                values.get("result"),
                values.get("login"),
                exc_info=True,
            )
            return False

    # ------------------------------------------------------------------
    # Purge
    # ------------------------------------------------------------------

    @api.model
    def _drkds_purge_days(self):
        """The retention in days from the setting, ``0`` meaning keep all."""
        raw = self.env["ir.config_parameter"].sudo().get_param(PURGE_DAYS_PARAM)
        if raw in (None, False, ""):
            return PURGE_DAYS_DEFAULT
        try:
            return max(int(raw), 0)
        except ValueError:
            _logger.warning(
                "drkds_login_history: ignoring invalid %s value %r", PURGE_DAYS_PARAM, raw
            )
            return PURGE_DAYS_DEFAULT

    @api.model
    def _cron_purge(self):
        """Delete rows older than the configured retention. Returns the count."""
        days = self._drkds_purge_days()
        if not days:
            return 0
        cutoff = fields.Datetime.now() - timedelta(days=days)
        old = self.sudo().search([("event_date", "<", cutoff)])
        count = len(old)
        old.unlink()
        if count:
            _logger.info(
                "drkds_login_history: purged %d login record(s) older than %d days",
                count,
                days,
            )
        return count
