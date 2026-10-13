"""End to end: three employees, passports and contracts, one renewal.

Day one, HR files the documents. The cron runs at three later dates, the
reminders appear exactly once for the right people, a renewed passport
replaces the old scan, and the missing-documents filter names who still has
a gap.
"""
import base64
from datetime import date

from freezegun import freeze_time

from odoo.tests import Form, tagged

from .common import TODAY, DocumentExpiryCommon


@tagged("post_install", "-at_install")
class TestDocumentScenario(DocumentExpiryCommon):
    def test_three_employees_through_a_year(self):
        officer_env = self.env(user=self.hr_officer)

        # 1. Day one: HR files passports for everyone and contracts for two.
        with freeze_time(TODAY):
            f = Form(officer_env["drkds.hr.document"])
            f.employee_id = self.emp_asha
            f.type_id = self.type_passport
            f.number = "P1234567"
            f.issue_date = date(2017, 1, 5)
            f.expiry_date = date(2027, 1, 4)        # 83 days out: inside the 90-day window
            f.file = self._file("asha passport v1")
            asha_passport = f.save()   # the binary widget fills file_name in the UI

            asha_contract = self._document(self.emp_asha, self.type_contract, date(2027, 3, 31))
            ravi_passport = self._document(self.emp_ravi, self.type_passport, date(2029, 6, 30))
            ravi_contract = self._document(self.emp_ravi, self.type_contract, date(2026, 10, 31))
            priya_passport = self._document(self.emp_priya, self.type_passport, date(2028, 2, 29))

            self.assertEqual(asha_passport.name, "Test Passport - Asha Nair")
            self.assertEqual(asha_passport.state, "expiring")
            self.assertEqual(asha_contract.state, "valid")
            self.assertEqual(ravi_passport.state, "valid")
            self.assertEqual(ravi_contract.state, "expiring")   # 18 days, window 30
            self.assertEqual(priya_passport.state, "valid")

            # Priya has no contract yet: she is the only one missing one.
            missing = self.Employee.search([("drkds_hr_missing_mandatory", "=", True)])
            self.assertEqual(missing & (self.emp_asha | self.emp_ravi | self.emp_priya), self.emp_priya)
            self.assertEqual(self.emp_priya.drkds_hr_missing_type_ids, self.type_contract)

            # 2. The nightly job: one reminder each for the two expiring documents.
            self.Document._cron_refresh_states()
            self.assertEqual(len(self._reminders()), 2)
            self.assertEqual(self._reminders(asha_passport).user_id, self.hr_officer)
            self.assertEqual(self._reminders(ravi_contract).user_id, self.hr_manager)
            self.assertFalse(self._reminders(ravi_passport))

        # 3. A week later the job runs again: nothing is duplicated.
        with freeze_time(date(2026, 10, 20)):
            self.Document._cron_refresh_states()
            self.assertEqual(len(self._reminders()), 2)

        # 4. Mid November: Ravi's contract has lapsed, the smart button says so.
        with freeze_time(date(2026, 11, 15)):
            self.Document._cron_refresh_states()
            self.assertEqual(ravi_contract.state, "expired")
            self.assertEqual(self.emp_ravi.drkds_hr_expired_document_count, 1)
            self.assertEqual(self.emp_ravi.drkds_hr_document_count, 2)
            expired = self.Employee.search([("drkds_hr_document_ids.state", "=", "expired")])
            self.assertEqual(expired & (self.emp_asha | self.emp_ravi | self.emp_priya), self.emp_ravi)

            # 5. Asha's new passport arrives. HR renews the same record: new
            #    number, dates and scan. The old file is gone, the reminder too.
            old_attachment = self.env["ir.attachment"].search([
                ("res_model", "=", "drkds.hr.document"),
                ("res_id", "=", asha_passport.id),
                ("res_field", "=", "file"),
            ])
            self.assertEqual(len(old_attachment), 1)
            f = Form(asha_passport.with_user(self.hr_officer))
            f.number = "P7654321"
            f.issue_date = date(2026, 11, 10)
            f.expiry_date = date(2036, 11, 9)
            f.file = self._file("asha passport v2")
            f.save()
            self.assertEqual(asha_passport.state, "valid")
            self.assertEqual(base64.b64decode(asha_passport.with_context(bin_size=False).file), b"asha passport v2")
            attachments = self.env["ir.attachment"].search([
                ("res_model", "=", "drkds.hr.document"),
                ("res_id", "=", asha_passport.id),
                ("res_field", "=", "file"),
            ])
            self.assertEqual(len(attachments), 1, "the renewal replaced the old scan, it did not add one")
            self.assertFalse(self._reminders(asha_passport))
            self.assertEqual(len(self._reminders()), 1, "only Ravi's contract reminder is left")

            # 6. Priya finally hands in a contract: the gap closes.
            self._document(self.emp_priya, self.type_contract, date(2027, 11, 14))
            self.assertFalse(self.emp_priya.drkds_hr_missing_mandatory)
            missing = self.Employee.search([("drkds_hr_missing_mandatory", "=", True)])
            self.assertFalse(missing & (self.emp_asha | self.emp_ravi | self.emp_priya))

        # 7. The list filters agree with the states.
        with freeze_time(date(2026, 11, 15)):
            self.Document._cron_refresh_states()
            docs = self.Document.search([("employee_id", "in", (self.emp_asha | self.emp_ravi | self.emp_priya).ids)])
            self.assertEqual(len(docs), 6)
            self.assertEqual(docs.filtered(lambda d: d.state == "expired"), ravi_contract)
            self.assertEqual(docs.filtered(lambda d: d.state == "expiring"), self.Document)
            self.assertEqual(len(docs.filtered(lambda d: d.state == "valid")), 5)
