# Part of the drkds free suite for Odoo 19 Community. See LICENSE (LGPL-3).
"""Unit tests: the rows a login writes, the purge, the guards, the parser.

Every figure asserted here is computed by hand from the records the test
itself creates, so a wrong count or a wrong cutoff cannot pass by accident.
"""

from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessDenied, AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user

from odoo.addons.drkds_login_history.models.drkds_login_record import (
    PURGE_DAYS_PARAM,
    parse_user_agent,
)

PASSWORD = "drkds-LH-pass-2026"


@tagged("post_install", "-at_install")
class TestLoginRecord(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Record = cls.env["drkds.login.record"]
        cls.Users = cls.env["res.users"]
        cls.user = new_test_user(
            cls.env, login="drkds_lh_user", password=PASSWORD, groups="base.group_user"
        )
        cls.plain = new_test_user(
            cls.env, login="drkds_lh_plain", groups="base.group_user"
        )
        cls.admin = new_test_user(
            cls.env, login="drkds_lh_admin", groups="base.group_user,base.group_system"
        )
        # The detached writer runs in its own environment; the users must be
        # in the table before it links rows to them.
        cls.env.flush_all()

    def setUp(self):
        super().setUp()
        # Outside test mode ``registry.cursor()`` opens a real second
        # connection, which cannot see this transaction's users and would
        # commit rows for real. Test mode nests it on the test transaction
        # instead, exactly as HttpCase does for HTTP requests.
        self.registry_enter_test_mode()

    def _rows(self, login):
        return self.Record.search([("login", "=", login)], order="id")

    def _authenticate(self, login, password):
        credential = {"type": "password", "login": login, "password": password}
        return self.Users.authenticate(credential, {"interactive": False})

    def _authenticate_denied(self, login, password):
        """Expect ``AccessDenied`` without ``self.assertRaises``.

        Odoo's ``assertRaises`` wraps its block in a savepoint and rolls it
        back once the expected exception fires, which would also undo the
        row the detached writer committed inside that block. A plain
        try/except keeps what the module wrote, as a real request does.
        """
        try:
            self._authenticate(login, password)
        except AccessDenied:
            return
        self.fail("AccessDenied was not raised for %s" % login)

    # ---------------------------------------------------------------- rows

    def test_successful_login_writes_success_row(self):
        auth_info = self._authenticate("drkds_lh_user", PASSWORD)
        self.assertEqual(auth_info["uid"], self.user.id)
        rows = self._rows("drkds_lh_user")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows.result, "success")
        self.assertEqual(rows.user_id, self.user)
        self.assertEqual(rows.login, "drkds_lh_user")
        self.assertFalse(rows.ip_address, "no HTTP request in a unit test")
        self.assertFalse(rows.country_name, "no geolocation is ever attempted")

    def test_failed_login_writes_failed_row_linked_to_user(self):
        self._authenticate_denied("drkds_lh_user", "not-the-password")
        rows = self._rows("drkds_lh_user")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows.result, "failed")
        self.assertEqual(rows.user_id, self.user, "resolved from the typed login")

    def test_unknown_login_writes_failed_row_without_user(self):
        self._authenticate_denied("drkds_nobody_here", "whatever")
        rows = self._rows("drkds_nobody_here")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows.result, "failed")
        self.assertFalse(rows.user_id)

    def test_logout_event_writes_logout_row(self):
        new_id = self.Record._drkds_log_event("logout", login="drkds_lh_user", uid=self.user.id)
        self.assertTrue(new_id)
        rows = self._rows("drkds_lh_user")
        self.assertEqual(rows.mapped("result"), ["logout"])
        self.assertEqual(rows.user_id, self.user)

    def test_sequence_of_events_is_kept_in_order(self):
        self._authenticate_denied("drkds_lh_user", "wrong-1")
        self._authenticate_denied("drkds_lh_user", "wrong-2")
        self._authenticate("drkds_lh_user", PASSWORD)
        self.Record._drkds_log_event("logout", login="drkds_lh_user", uid=self.user.id)
        self.assertEqual(
            self._rows("drkds_lh_user").mapped("result"),
            ["failed", "failed", "success", "logout"],
        )

    # -------------------------------------------------------------- guards

    def test_detached_writer_never_raises(self):
        """An unwritable row is logged and dropped, the login is not blocked."""
        with self.assertLogs("odoo.addons.drkds_login_history", level="WARNING") as captured:
            result = self.Record._drkds_write_detached(
                {"result": "failed", "login": "x", "no_such_column": 1}
            )
        self.assertFalse(result)
        self.assertTrue(any("could not record" in line for line in captured.output))
        self.assertFalse(self._rows("x"))

    def test_admin_only_access(self):
        self.Record._drkds_log_event("success", login="drkds_lh_user", uid=self.user.id)
        with self.assertRaises(AccessError):
            self.Record.with_user(self.plain).search([("login", "=", "drkds_lh_user")])
        with self.assertRaises(AccessError):
            self.Record.with_user(self.plain).create({"result": "success"})
        admin_rows = self.Record.with_user(self.admin).search([("login", "=", "drkds_lh_user")])
        self.assertEqual(len(admin_rows), 1)
        with self.assertRaises(AccessError):
            admin_rows.write({"login": "tampered"})
        with self.assertRaises(AccessError):
            self.Record.with_user(self.admin).create({"result": "success"})
        admin_rows.unlink()
        self.assertFalse(self._rows("drkds_lh_user"))

    # --------------------------------------------------------------- purge

    def _make(self, days_ago, result="success"):
        return self.Record.sudo().create(
            {
                "result": result,
                "login": "drkds_lh_user",
                "user_id": self.user.id,
                "event_date": fields.Datetime.now() - timedelta(days=days_ago),
            }
        )

    def test_purge_removes_only_older_than_setting(self):
        self.env["ir.config_parameter"].sudo().set_param(PURGE_DAYS_PARAM, "30")
        old_1 = self._make(31)
        old_2 = self._make(200, "failed")
        edge = self._make(29)
        fresh = self._make(0, "logout")
        removed = self.Record._cron_purge()
        self.assertEqual(removed, 2)
        self.assertFalse(old_1.exists())
        self.assertFalse(old_2.exists())
        self.assertTrue(edge.exists())
        self.assertTrue(fresh.exists())

    def test_purge_default_is_180_days(self):
        self.env["ir.config_parameter"].sudo().set_param(PURGE_DAYS_PARAM, False)
        self.assertEqual(self.Record._drkds_purge_days(), 180)
        older = self._make(181)
        newer = self._make(179)
        self.assertEqual(self.Record._cron_purge(), 1)
        self.assertFalse(older.exists())
        self.assertTrue(newer.exists())

    def test_purge_zero_keeps_everything(self):
        self.env["ir.config_parameter"].sudo().set_param(PURGE_DAYS_PARAM, "0")
        ancient = self._make(5000)
        self.assertEqual(self.Record._cron_purge(), 0)
        self.assertTrue(ancient.exists())

    def test_purge_setting_round_trips_through_settings(self):
        settings = self.env["res.config.settings"].create(
            {"drkds_login_history_purge_days": 45}
        )
        settings.execute()
        self.assertEqual(self.Record._drkds_purge_days(), 45)

    # ------------------------------------------------------- user figures

    def test_user_form_figures(self):
        last = self._make(3)
        self._make(10)
        self._make(0, "failed")
        self._make(0, "failed")
        self._make(2, "failed")
        self.user.invalidate_recordset(["drkds_last_login_date", "drkds_failed_today"])
        self.assertEqual(self.user.drkds_last_login_date, last.event_date)
        self.assertEqual(self.user.drkds_failed_today, 2)
        self.assertEqual(self.plain.drkds_failed_today, 0)
        self.assertFalse(self.plain.drkds_last_login_date)
        action = self.user.action_drkds_open_login_history()
        self.assertEqual(action["res_model"], "drkds.login.record")
        self.assertEqual(action["domain"], [("user_id", "=", self.user.id)])

    # -------------------------------------------------------------- parser

    def test_user_agent_parser(self):
        cases = [
            (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
                ("Edge", "Windows"),
            ),
            (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36",
                ("Chrome", "Linux"),
            ),
            (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) "
                "Gecko/20100101 Firefox/125.0",
                ("Firefox", "macOS"),
            ),
            (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 "
                "(KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
                ("Safari", "iOS"),
            ),
            (
                "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Mobile Safari/537.36 OPR/80.0",
                ("Opera", "Android"),
            ),
            ("Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko",
             ("Internet Explorer", "Windows")),
            ("python-requests/2.31.0", ("Other", "Other")),
            ("", ("Unknown", "Unknown")),
            (None, ("Unknown", "Unknown")),
        ]
        for text, expected in cases:
            with self.subTest(user_agent=text):
                self.assertEqual(parse_user_agent(text), expected)
