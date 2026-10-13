from datetime import date, timedelta

from freezegun import freeze_time

from odoo import fields
from odoo.tests import tagged

from .common import DocumentsCommon


@tagged("post_install", "-at_install")
class TestExpiry(DocumentsCommon):
    def setUp(self):
        super().setUp()
        self.today = fields.Date.today()

    def _run_cron(self):
        return self.Document._cron_drkds_expiry_reminder()

    def test_activity_seven_days_before_expiry(self):
        doc = self._document(name="Licence", user_id=self.clerk.id,
                             expiry_date=self.today + timedelta(days=7))
        reminded = self._run_cron()
        self.assertEqual(reminded, doc)
        acts = self._activities(doc)
        self.assertEqual(len(acts), 1)
        self.assertEqual(acts.user_id, self.clerk)
        self.assertEqual(acts.date_deadline, doc.expiry_date)
        self.assertEqual(acts.activity_type_id, self.env.ref("mail.mail_activity_data_todo"))
        self.assertIn(fields.Date.to_string(doc.expiry_date), acts.summary)
        self.assertEqual(doc.expiry_reminded_date, doc.expiry_date)

    def test_eight_days_out_is_too_early(self):
        doc = self._document(user_id=self.clerk.id, expiry_date=self.today + timedelta(days=8))
        self.assertFalse(self._run_cron())
        self.assertFalse(self._activities(doc))

    def test_no_expiry_no_reminder(self):
        doc = self._document(user_id=self.clerk.id)
        self.assertFalse(self._run_cron())
        self.assertFalse(self._activities(doc))

    def test_cron_is_idempotent(self):
        doc = self._document(user_id=self.clerk.id, expiry_date=self.today + timedelta(days=3))
        self._run_cron()
        self._run_cron()
        self.assertEqual(len(self._activities(doc)), 1)

    def test_moving_the_expiry_date_reminds_again(self):
        doc = self._document(user_id=self.clerk.id, expiry_date=self.today + timedelta(days=3))
        self._run_cron()
        doc.expiry_date = self.today + timedelta(days=5)
        self.assertEqual(self._run_cron(), doc)
        self.assertEqual(len(self._activities(doc)), 2)
        doc.expiry_date = self.today + timedelta(days=30)
        self.assertFalse(self._run_cron())

    def test_already_expired_document_is_reminded_once(self):
        doc = self._document(user_id=self.clerk.id, expiry_date=self.today - timedelta(days=2))
        self.assertEqual(self._run_cron(), doc)
        self.assertFalse(self._run_cron())

    def test_document_without_owner_waits_for_one(self):
        """The job runs as OdooBot; a to-do for OdooBot is read by nobody. A
        document with no owner, or an archived one, gets no to-do and is not
        marked as reminded, so it is reminded once someone owns it."""
        ownerless = self._document(user_id=False, expiry_date=self.today + timedelta(days=1))
        gone = self.env["res.users"].create({
            "name": "Left the company", "login": "drkds_docl_gone",
            "group_ids": [(6, 0, self.env.ref("drkds_documents_lite.group_document_user").ids)],
        })
        orphaned = self._document(user_id=gone.id, expiry_date=self.today + timedelta(days=1))
        gone.active = False
        self.assertFalse(self._run_cron())
        self.assertFalse(self._activities(ownerless))
        self.assertFalse(self._activities(orphaned))
        self.assertFalse(ownerless.expiry_reminded_date)
        ownerless.user_id = self.clerk
        self.assertEqual(self._run_cron(), ownerless)
        self.assertEqual(self._activities(ownerless).user_id, self.clerk)

    def test_an_owner_who_cannot_open_the_document_gets_no_to_do(self):
        """An activity subscribes and notifies its assignee; an owner outside
        the folder's groups would be told about a document they cannot read."""
        nda = self._document(name="NDA", folder_id=self.folder_legal.id,
                             user_id=self.clerk.id, expiry_date=self.today + timedelta(days=3))
        self.assertFalse(self._run_cron())
        self.assertFalse(self._activities(nda))
        self.assertNotIn(self.clerk.partner_id, nda.message_partner_ids)
        self.assertFalse(nda.expiry_reminded_date)
        nda.user_id = self.lawyer
        self.assertEqual(self._run_cron(), nda)
        self.assertEqual(self._activities(nda).user_id, self.lawyer)

    def test_today_is_the_owner_s_date(self):
        """The job runs with no timezone, so its own date is UTC. At 20:00 UTC
        on 13 October it is already 01:30 on 14 October in India: a document
        expiring on 21 October is seven days away for an owner there, eight
        for an owner on UTC."""
        self.clerk.tz = "Asia/Kolkata"
        self.lawyer.tz = "UTC"
        with freeze_time("2026-10-13 20:00:00"):
            india = self._document(name="India", user_id=self.clerk.id, expiry_date=date(2026, 10, 21))
            utc = self._document(name="UTC", user_id=self.lawyer.id, expiry_date=date(2026, 10, 21))
            self.assertEqual(self._run_cron(), india)
            self.assertFalse(self._activities(utc))
        with freeze_time("2026-10-14 08:00:00"):
            self.assertEqual(self._run_cron(), utc)
