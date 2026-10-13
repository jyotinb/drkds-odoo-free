# Part of the drkds free suite for Odoo 19 Community. See LICENSE (LGPL-3).
"""End-to-end scenario through the real HTTP login form.

A user mistypes the password twice, gets in on the third try and signs out.
The table must then hold exactly those four rows, in that order, with the
request details filled in. The form route (``/web/login``) is used rather
than the JSON one because that is what a person at a browser goes through.
"""

import re

from odoo.tests import HttpCase, tagged
from odoo.tests.common import new_test_user

LOGIN = "drkds_lh_web"
PASSWORD = "drkds-LH-web-2026"


@tagged("post_install", "-at_install")
class TestLoginScenario(HttpCase):
    def setUp(self):
        super().setUp()
        self.user = new_test_user(
            self.env, login=LOGIN, password=PASSWORD, groups="base.group_user"
        )
        self.Record = self.env["drkds.login.record"]
        self.env.flush_all()

    def _csrf_token(self):
        page = self.url_open("/web/login")
        self.assertEqual(page.status_code, 200)
        match = re.search(r'name="csrf_token"\s+value="([^"]+)"', page.text)
        self.assertTrue(match, "login form carries no CSRF token")
        return match.group(1)

    def _post_login(self, password):
        return self.url_open(
            "/web/login",
            data={"login": LOGIN, "password": password, "csrf_token": self._csrf_token()},
            allow_redirects=False,
        )

    def test_two_wrong_passwords_then_right_then_logout(self):
        self.assertFalse(self.Record.search([("login", "=", LOGIN)]))

        for wrong in ("wrong-one", "wrong-two"):
            response = self._post_login(wrong)
            self.assertEqual(response.status_code, 200, "the form is shown again")
            self.assertIn("oe_login_form", response.text)

        response = self._post_login(PASSWORD)
        self.assertEqual(response.status_code, 303)
        self.assertIn("/odoo", response.headers.get("Location", ""))

        response = self.url_open("/web/session/logout", allow_redirects=False)
        self.assertEqual(response.status_code, 303)

        rows = self.Record.search([("login", "=", LOGIN)], order="id")
        self.assertEqual(rows.mapped("result"), ["failed", "failed", "success", "logout"])
        self.assertEqual(rows.mapped("user_id"), self.user, "every row links the user")
        for row in rows:
            self.assertEqual(row.ip_address, "127.0.0.1")
            self.assertIn("python-requests", row.user_agent)
            self.assertEqual(row.browser, "Other")
            self.assertEqual(row.os_name, "Other")
            self.assertRegex(row.session_hash, r"^[0-9a-f]{64}$")
            self.assertFalse(row.country_name)
        self.assertEqual(rows[-1].result, "logout")
        self.user.invalidate_recordset(["drkds_last_login_date", "drkds_failed_today"])
        self.assertEqual(self.user.drkds_failed_today, 2)
        self.assertEqual(self.user.drkds_last_login_date, rows[2].event_date)
