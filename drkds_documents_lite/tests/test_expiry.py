from datetime import timedelta

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
        doc = self._document(expiry_date=self.today + timedelta(days=8))
        self.assertFalse(self._run_cron())
        self.assertFalse(self._activities(doc))

    def test_no_expiry_no_reminder(self):
        doc = self._document()
        self.assertFalse(self._run_cron())
        self.assertFalse(self._activities(doc))

    def test_cron_is_idempotent(self):
        doc = self._document(expiry_date=self.today + timedelta(days=3))
        self._run_cron()
        self._run_cron()
        self.assertEqual(len(self._activities(doc)), 1)

    def test_moving_the_expiry_date_reminds_again(self):
        doc = self._document(expiry_date=self.today + timedelta(days=3))
        self._run_cron()
        doc.expiry_date = self.today + timedelta(days=5)
        self.assertEqual(self._run_cron(), doc)
        self.assertEqual(len(self._activities(doc)), 2)
        doc.expiry_date = self.today + timedelta(days=30)
        self.assertFalse(self._run_cron())

    def test_already_expired_document_is_reminded_once(self):
        doc = self._document(expiry_date=self.today - timedelta(days=2))
        self.assertEqual(self._run_cron(), doc)
        self.assertFalse(self._run_cron())

    def test_document_without_owner_goes_to_the_running_user(self):
        doc = self._document(user_id=False, expiry_date=self.today + timedelta(days=1))
        self._run_cron()
        self.assertEqual(self._activities(doc).user_id, self.env.user)
