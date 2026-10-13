# Part of the drkds free suite for Odoo 19 Community. See LICENSE (LGPL-3).
"""Every other way into Odoo, end to end over HTTP.

``test_scenario`` covers the browser form. Here: the JSON-RPC login and
logout used by external and mobile clients, the XML-RPC login with a password
and with an API key, and a two-factor login (wrong code, right code, then a
remembered browser).

Exceptions are caught by hand, never with ``assertRaises``: Odoo's version
rolls a savepoint back when the exception fires, which would also undo the
rows the server committed in the meantime.
"""

import base64
import hashlib
import hmac
import re
import struct
import time
from datetime import timedelta

from odoo import fields
from odoo.tests import HttpCase, tagged
from odoo.tests.common import get_db_name, new_test_user

LOGIN = "drkds_lh_paths"
PASSWORD = "drkds-LH-paths-2026"
BROWSER = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"


def totp_code(secret, at):
    """RFC 6238 code (SHA-1, 6 digits, 30 s), as an authenticator app shows it."""
    key = base64.b32decode(secret)
    digest = hmac.new(key, struct.pack(">Q", int(at) // 30), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return "%06d" % (value % 1000000)


@tagged("post_install", "-at_install")
class TestLoginPaths(HttpCase):
    def setUp(self):
        super().setUp()
        self.user = new_test_user(
            self.env, login=LOGIN, password=PASSWORD, groups="base.group_user"
        )
        self.Record = self.env["drkds.login.record"]
        self.env.flush_all()

    def _rows(self):
        return self.Record.search([("login", "=", LOGIN)], order="id")

    def _jsonrpc(self, route, params=None):
        response = self.url_open(
            route,
            json={"jsonrpc": "2.0", "method": "call", "id": 0, "params": params or {}},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def _csrf(self, url, headers):
        page = self.url_open(url, headers=headers, allow_redirects=False)
        self.assertEqual(page.status_code, 200, url)
        match = re.search(r'name="csrf_token"\s+value="([^"]+)"', page.text)
        self.assertTrue(match, "%s carries no CSRF token" % url)
        return match.group(1)

    # ---------------------------------------------------------- JSON-RPC

    def test_json_rpc_login_and_destroy(self):
        # /web/session/destroy is a read-only route that has already queried
        # through its cursor when the logout row is written. In production
        # the row goes through a separate read/write connection; in test mode
        # every cursor shares the test transaction, which the read-only
        # simulation would have marked READ ONLY. Core tests of read-only
        # routes that write elsewhere (website visitors) switch it off too.
        self.set_registry_readonly_mode(False)
        self.addCleanup(self.set_registry_readonly_mode, True)
        # A wrong password is not tried here: this route lets AccessDenied
        # escape, so the request is rolled back, and in test mode the
        # detached writer is only a savepoint inside that same transaction.
        # On a real server it is a connection of its own and the row stays;
        # that cannot be reproduced in a test. The unit tests cover the row
        # itself, test_scenario the form route that does not roll back.
        db = get_db_name()
        reply = self._jsonrpc(
            "/web/session/authenticate", {"db": db, "login": LOGIN, "password": PASSWORD}
        )
        self.assertEqual(reply["result"]["uid"], self.user.id)
        reply = self._jsonrpc("/web/session/destroy")
        self.assertNotIn("error", reply)

        rows = self._rows()
        self.assertEqual(rows.mapped("result"), ["success", "logout"])
        self.assertEqual(rows.mapped("user_id"), self.user)
        self.assertEqual(set(rows.mapped("ip_address")), {"127.0.0.1"})

    # ----------------------------------------------------------- XML-RPC

    def test_xmlrpc_login_and_api_key_calls(self):
        """``authenticate`` is a login and gets a row; the calls that follow
        are not logins, so an integration making thousands of API-key calls
        adds nothing to the table."""
        db = get_db_name()
        self.assertFalse(self.xmlrpc_common.authenticate(db, LOGIN, "wrong", {}))
        uid = self.xmlrpc_common.authenticate(db, LOGIN, PASSWORD, {})
        self.assertEqual(uid, self.user.id)
        key = self.env["res.users.apikeys"].with_user(self.user).sudo()._generate(
            None, "drkds login history test", fields.Datetime.now() + timedelta(days=1)
        )
        self.env.flush_all()
        self.assertEqual(self.xmlrpc_common.authenticate(db, LOGIN, key, {}), uid)
        for _call in range(5):
            self.xmlrpc_object.execute_kw(db, uid, key, "res.partner", "search_count", [[]])

        rows = self._rows()
        self.assertEqual(rows.mapped("result"), ["failed", "success", "success"])
        self.assertEqual(rows.mapped("user_id"), self.user)
        # Odoo hides the HTTP request from its RPC services (core's own log
        # line reads "from n/a"), so these rows carry no address or browser.
        self.assertFalse(any(rows.mapped("ip_address")))
        self.assertFalse(any(rows.mapped("user_agent")))

    # --------------------------------------------------------------- 2FA

    def test_two_factor_login(self):
        """Right password, wrong code, right code, then a remembered browser.

        The password step alone must never read as a successful login: the
        session is only signed in once the second factor is accepted.
        """
        if "auth_totp.device" not in self.env:
            self.skipTest("auth_totp is not installed")
        secret = base64.b32encode(b"drkds-login-hist-2fa").decode()
        self.user.sudo().totp_secret = secret
        self.env.flush_all()
        headers = {"User-Agent": BROWSER}

        def password_step():
            response = self.url_open(
                "/web/login",
                data={
                    "login": LOGIN,
                    "password": PASSWORD,
                    "csrf_token": self._csrf("/web/login", headers),
                },
                headers=headers,
                allow_redirects=False,
            )
            self.assertEqual(response.status_code, 303)
            self.assertIn("/web/login/totp", response.headers["Location"])

        def code_step(code, remember=False):
            data = {"totp_token": code, "csrf_token": self._csrf("/web/login/totp", headers)}
            if remember:
                data["remember"] = "1"
            return self.url_open(
                "/web/login/totp", data=data, headers=headers, allow_redirects=False
            )

        password_step()
        now = time.time()
        valid = {totp_code(secret, now + step * 30) for step in (-2, -1, 0, 1, 2)}
        wrong = next(code for code in ("000000", "111111", "222222") if code not in valid)
        response = code_step(wrong)
        self.assertEqual(response.status_code, 200, "the code form is shown again")
        response = code_step(totp_code(secret, now), remember=True)
        self.assertEqual(response.status_code, 303)
        self.assertTrue(self.opener.cookies.get("td_id"), "browser remembered")
        response = self.url_open("/web/session/logout", headers=headers, allow_redirects=False)
        self.assertEqual(response.status_code, 303)

        # From the remembered browser Odoo signs in without asking a code.
        password_step()
        response = self.url_open("/web/login/totp", headers=headers, allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertNotIn("/web/login", response.headers["Location"])

        rows = self._rows()
        self.assertEqual(
            rows.mapped("result"), ["mfa_pending", "failed", "success", "logout", "success"]
        )
        self.assertEqual(rows.mapped("user_id"), self.user)
        # One login attempt, one session: the three rows share its hash.
        self.assertEqual(len(set(rows[:3].mapped("session_hash"))), 1)
        self.assertEqual(set(rows.mapped("browser")), {"Firefox"})
        self.user.invalidate_recordset(["drkds_last_login_date", "drkds_failed_today"])
        self.assertEqual(self.user.drkds_failed_today, 1, "the wrong code")
        self.assertEqual(self.user.drkds_last_login_date, rows[4].event_date)
