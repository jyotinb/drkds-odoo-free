from datetime import date, timedelta

from freezegun import freeze_time
from psycopg2.errors import CheckViolation, ForeignKeyViolation

from odoo import SUPERUSER_ID
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import new_test_user, tagged
from odoo.tools import mute_logger

from .common import TODAY, DocumentExpiryCommon


@tagged("post_install", "-at_install")
class TestDocumentState(DocumentExpiryCommon):
    """State at frozen dates. Passport window is 90 days, contract 30."""

    @freeze_time(TODAY)
    def test_valid_outside_window(self):
        # 2026-10-13 + 91 days = 2027-01-12: one day outside the 90-day window
        doc = self._document(self.emp_asha, self.type_passport, date(2027, 1, 12))
        self.assertEqual(doc.state, "valid")
        self.assertEqual(doc.days_to_expiry, 91)

    @freeze_time(TODAY)
    def test_expiring_on_window_edge(self):
        # exactly 90 days ahead is the first expiring day
        doc = self._document(self.emp_asha, self.type_passport, date(2027, 1, 11))
        self.assertEqual(doc.state, "expiring")
        self.assertEqual(doc.days_to_expiry, 90)

    @freeze_time(TODAY)
    def test_expiring_today_is_not_expired(self):
        doc = self._document(self.emp_asha, self.type_contract, TODAY)
        self.assertEqual(doc.state, "expiring")
        self.assertEqual(doc.days_to_expiry, 0)

    @freeze_time(TODAY)
    def test_expired_yesterday(self):
        doc = self._document(self.emp_asha, self.type_contract, date(2026, 10, 12))
        self.assertEqual(doc.state, "expired")
        self.assertEqual(doc.days_to_expiry, -1)

    @freeze_time(TODAY)
    def test_no_expiry_is_valid(self):
        doc = self._document(self.emp_asha, self.type_certificate, None)
        self.assertEqual(doc.state, "valid")
        self.assertEqual(doc.days_to_expiry, 0)

    @freeze_time(TODAY)
    def test_window_follows_the_type(self):
        """Contract at 45 days is valid (window 30); widening the window to
        60 flips it to expiring without touching the document."""
        doc = self._document(self.emp_asha, self.type_contract, TODAY + timedelta(days=45))
        self.assertEqual(doc.state, "valid")
        self.type_contract.remind_days = 60
        self.assertEqual(doc.state, "expiring")

    def test_name_is_type_and_employee(self):
        doc = self._document(self.emp_ravi, self.type_passport, date(2030, 1, 1))
        self.assertEqual(doc.name, "Test Passport - Ravi Menon")
        self.assertEqual(doc.company_id, self.company)

    # -- constraints ----------------------------------------------------
    def test_expiry_required_by_type(self):
        with self.assertRaises(ValidationError):
            self._document(self.emp_asha, self.type_passport, None)

    def test_expiry_before_issue_refused(self):
        with self.assertRaises(ValidationError):
            self._document(
                self.emp_asha, self.type_passport, date(2027, 1, 1),
                issue_date=date(2027, 6, 1),
            )

    @mute_logger("odoo.sql_db")
    def test_negative_remind_days_refused(self):
        with self.assertRaises(CheckViolation):
            self.DocType.create({"name": "Bad", "remind_days": -1})
            self.env.flush_all()

    def test_type_in_use_cannot_be_deleted(self):
        self._document(self.emp_asha, self.type_passport, date(2030, 1, 1))
        with mute_logger("odoo.sql_db"), self.assertRaises(ForeignKeyViolation):
            self.type_passport.unlink()

    @freeze_time(TODAY)
    def test_state_cannot_be_written(self):
        """An RPC write or an import cannot mark an expired document valid."""
        doc = self._document(self.emp_asha, self.type_contract, date(2026, 10, 1))
        self.assertEqual(doc.state, "expired")
        doc.with_user(self.hr_officer).write({"state": "valid", "note": "Checked"})
        self.env.invalidate_all()
        self.assertEqual(doc.state, "expired")
        self.assertEqual(doc.note, "Checked")

    def test_date_on_type_without_expiry_is_honoured(self):
        """A type without expiry does not demand a date, but one entered
        anyway still drives the status: a lapsed date never reads Valid."""
        with freeze_time(TODAY):
            doc = self._document(self.emp_asha, self.type_certificate, date(2026, 10, 1))
            self.assertEqual(doc.state, "expired")


@tagged("post_install", "-at_install")
class TestCron(DocumentExpiryCommon):
    def test_cron_moves_states_as_days_pass(self):
        """Created valid; 61 days later expiring; after expiry expired. The
        record is never written between the runs, as in production."""
        with freeze_time(TODAY):
            doc = self._document(self.emp_asha, self.type_contract, date(2026, 12, 13))
            self.assertEqual(doc.state, "valid")
        with freeze_time(date(2026, 11, 13)):  # 30 days before: window opens
            self.Document._cron_refresh_states()
            self.assertEqual(doc.state, "expiring")
        with freeze_time(date(2026, 12, 13)):  # expiry day: still expiring
            self.Document._cron_refresh_states()
            self.assertEqual(doc.state, "expiring")
        with freeze_time(date(2026, 12, 14)):
            self.Document._cron_refresh_states()
            self.assertEqual(doc.state, "expired")

    def test_one_activity_only(self):
        with freeze_time(TODAY):
            doc = self._document(self.emp_asha, self.type_passport, date(2026, 12, 1))
            self.assertEqual(doc.state, "expiring")
            self.assertFalse(self._reminders(doc))
            self.Document._cron_refresh_states()
            self.Document._cron_refresh_states()
            self.Document._cron_refresh_states()
        reminders = self._reminders(doc)
        self.assertEqual(len(reminders), 1)
        self.assertEqual(reminders.user_id, self.hr_officer, "the employee's HR responsible")
        self.assertEqual(reminders.date_deadline, date(2026, 12, 1))
        self.assertIn("Test Passport", reminders.summary)
        self.assertIn("Asha Nair", reminders.summary)

    def test_valid_documents_get_no_activity(self):
        with freeze_time(TODAY):
            doc = self._document(self.emp_asha, self.type_passport, date(2030, 1, 1))
            self.Document._cron_refresh_states()
        self.assertFalse(self._reminders(doc))

    def test_expired_document_keeps_its_single_reminder(self):
        """The reminder raised while expiring is not duplicated once expired."""
        with freeze_time(TODAY):
            doc = self._document(self.emp_asha, self.type_contract, date(2026, 10, 20))
            self.Document._cron_refresh_states()
        with freeze_time(date(2026, 11, 1)):
            self.Document._cron_refresh_states()
        self.assertEqual(doc.state, "expired")
        self.assertEqual(len(self._reminders(doc)), 1)

    def test_fallback_user_from_settings(self):
        self.company.drkds_hr_document_responsible_id = self.fallback_user
        # The HR responsible is NOT NULL on hr.version, so the real gap is a
        # responsible who has left: archive Ravi's.
        self.hr_manager.action_archive()
        self.assertFalse(self.emp_ravi.hr_responsible_id.active)
        with freeze_time(TODAY):
            doc = self._document(self.emp_ravi, self.type_contract, date(2026, 10, 20))
            self.Document._cron_refresh_states()
        self.assertEqual(self._reminders(doc).user_id, self.fallback_user)

    def test_settings_form_round_trip(self):
        settings = self.env["res.config.settings"].create({
            "drkds_hr_document_responsible_id": self.fallback_user.id,
        })
        settings.execute()
        self.assertEqual(self.company.drkds_hr_document_responsible_id, self.fallback_user)

    @mute_logger("odoo.addons.drkds_hr_document_expiry_lite.models.drkds_hr_document")
    def test_no_user_at_all_skips_quietly(self):
        self.company.drkds_hr_document_responsible_id = False
        self.hr_manager.action_archive()
        with freeze_time(TODAY):
            doc = self._document(self.emp_ravi, self.type_contract, date(2026, 10, 20))
            self.Document._cron_refresh_states()
        self.assertFalse(self._reminders(doc))

    def test_renewal_clears_reminder_and_state(self):
        with freeze_time(TODAY):
            doc = self._document(self.emp_asha, self.type_contract, date(2026, 10, 20))
            self.Document._cron_refresh_states()
            self.assertEqual(len(self._reminders(doc)), 1)
            doc.write({
                "expiry_date": date(2027, 10, 20),
                "file": self._file("renewed scan"),
                "file_name": "renewed.pdf",
            })
            self.assertEqual(doc.state, "valid")
            self.assertFalse(self._reminders(doc))
            self.Document._cron_refresh_states()
            self.assertFalse(self._reminders(doc))

    def _run_cron_as_scheduler(self):
        """The job as ir.cron runs it: OdooBot, a context without timezone."""
        self.Document.with_env(self.env(user=SUPERUSER_ID, context={}))._cron_refresh_states()

    def test_cron_dates_the_status_in_the_employee_timezone(self):
        """20:51 UTC on 13 Oct is 02:21 on 14 Oct in India and 16:51 on 13 Oct
        in New York; 02:00 UTC on 14 Oct is 07:30 on 14 Oct in India and
        22:00 on 13 Oct in New York. A contract ending on 13 Oct is expired
        for the Indian employee at both instants and still expiring for the
        New York one, whatever the UTC date says."""
        self.emp_ravi.tz = "America/New_York"
        with freeze_time("2026-10-13 06:00:00"):
            india = self._document(self.emp_asha, self.type_contract, date(2026, 10, 13))
            new_york = self._document(self.emp_ravi, self.type_contract, date(2026, 10, 13))
        for instant in ("2026-10-13 20:51:10", "2026-10-14 02:00:00"):
            with freeze_time(instant):
                self._run_cron_as_scheduler()
                self.env.invalidate_all()
                self.assertEqual((india.state, india.days_to_expiry), ("expired", -1), instant)
                self.assertEqual((new_york.state, new_york.days_to_expiry), ("expiring", 0), instant)

    def test_responsible_without_hr_rights_falls_back(self):
        """An activity for someone who cannot open the document is no
        reminder: the fallback HR officer gets it instead."""
        self.company.drkds_hr_document_responsible_id = self.fallback_user
        self.emp_ravi.hr_responsible_id = self.plain_user
        with freeze_time(TODAY):
            doc = self._document(self.emp_ravi, self.type_contract, date(2026, 10, 20))
            self._run_cron_as_scheduler()
        reminder = self._reminders(doc)
        self.assertEqual(reminder.user_id, self.fallback_user)
        doc.with_user(reminder.user_id).check_access("read")

    def test_responsible_outside_the_company_falls_back(self):
        other = self.env["res.company"].create({"name": "Other Co"})
        other_hr = new_test_user(
            self.env, login="drkds_hdl_other_hr", name="Other Co HR",
            groups="base.group_user,hr.group_hr_user",
            company_id=other.id, company_ids=[(6, 0, other.ids)],
        )
        self.company.drkds_hr_document_responsible_id = self.fallback_user
        self.emp_ravi.hr_responsible_id = other_hr
        with freeze_time(TODAY):
            doc = self._document(self.emp_ravi, self.type_contract, date(2026, 10, 20))
            self._run_cron_as_scheduler()
        self.assertEqual(self._reminders(doc).user_id, self.fallback_user)

    @mute_logger("odoo.addons.drkds_hr_document_expiry_lite.models.drkds_hr_document")
    def test_unfit_fallback_is_not_assigned(self):
        """A fallback without HR rights is skipped like a missing one."""
        self.company.drkds_hr_document_responsible_id = self.plain_user
        self.emp_ravi.hr_responsible_id = self.plain_user
        with freeze_time(TODAY):
            doc = self._document(self.emp_ravi, self.type_contract, date(2026, 10, 20))
            self._run_cron_as_scheduler()
        self.assertEqual(doc.state, "expiring")
        self.assertFalse(self._reminders(doc))

    def test_departed_employee_gets_no_reminder(self):
        with freeze_time(TODAY):
            doc = self._document(self.emp_priya, self.type_contract, date(2026, 10, 20))
            self.emp_priya.action_archive()
            self.assertFalse(self.emp_priya.active)
            self._run_cron_as_scheduler()
        self.assertEqual(doc.state, "expiring")
        self.assertFalse(self._reminders(doc))

    def test_cron_refreshes_archived_documents_without_reminding(self):
        with freeze_time(TODAY):
            doc = self._document(self.emp_asha, self.type_contract, date(2026, 12, 13))
            self.assertEqual(doc.state, "valid")  # computed and stored now, as in production
            doc.action_archive()
        with freeze_time(date(2026, 11, 20)):  # inside the 30-day window
            self._run_cron_as_scheduler()
            self.assertEqual(doc.state, "expiring")
            self.assertFalse(self._reminders(doc))
        with freeze_time(date(2026, 12, 14)):
            self._run_cron_as_scheduler()
            self.assertEqual(doc.state, "expired")

    def test_cron_record_exists_and_is_daily(self):
        cron = self.env.ref("drkds_hr_document_expiry_lite.ir_cron_drkds_hr_document_refresh")
        self.assertTrue(cron.active)
        self.assertEqual((cron.interval_number, cron.interval_type), (1, "days"))


@tagged("post_install", "-at_install")
class TestEmployee(DocumentExpiryCommon):
    def _missing(self, operator="=", value=True):
        return self.Employee.search([
            ("drkds_hr_missing_mandatory", operator, value),
            ("id", "in", (self.emp_asha | self.emp_ravi | self.emp_priya).ids),
        ])

    def test_missing_mandatory_filter(self):
        # Asha: both. Ravi: passport only. Priya: nothing.
        self._document(self.emp_asha, self.type_passport, date(2030, 1, 1))
        self._document(self.emp_asha, self.type_contract, date(2030, 1, 1))
        self._document(self.emp_ravi, self.type_passport, date(2030, 1, 1))
        self.assertEqual(self._missing(), self.emp_ravi | self.emp_priya)
        self.assertEqual(self._missing("!=", True), self.emp_asha)
        self.assertEqual(self._missing("=", False), self.emp_asha)
        self.assertEqual(self._missing("in", [True]), self.emp_ravi | self.emp_priya)
        self.assertEqual(self._missing("not in", [True]), self.emp_asha)
        self.assertEqual(self.emp_ravi.drkds_hr_missing_type_ids, self.type_contract)
        self.assertEqual(self.emp_priya.drkds_hr_missing_type_ids, self.type_passport | self.type_contract)
        self.assertFalse(self.emp_asha.drkds_hr_missing_mandatory)

    def test_archived_document_counts_as_missing(self):
        doc = self._document(self.emp_asha, self.type_passport, date(2030, 1, 1))
        self._document(self.emp_asha, self.type_contract, date(2030, 1, 1))
        self.assertNotIn(self.emp_asha, self._missing())
        doc.active = False
        self.assertIn(self.emp_asha, self._missing())
        self.assertEqual(self.emp_asha.drkds_hr_missing_type_ids, self.type_passport)

    def test_non_mandatory_type_is_ignored(self):
        self.type_passport.mandatory = False
        self.type_contract.mandatory = False
        self.assertFalse(self._missing())
        self.assertEqual(self._missing("=", False), self.emp_asha | self.emp_ravi | self.emp_priya)

    def test_other_company_type_is_ignored(self):
        other = self.env["res.company"].create({"name": "Other Co"})
        self.DocType.create({
            "name": "Other Co Licence", "mandatory": True, "company_id": other.id,
        })
        self._document(self.emp_asha, self.type_passport, date(2030, 1, 1))
        self._document(self.emp_asha, self.type_contract, date(2030, 1, 1))
        self.assertFalse(self.emp_asha.drkds_hr_missing_mandatory)

    @freeze_time(TODAY)
    def test_smart_button_counts(self):
        self._document(self.emp_asha, self.type_passport, date(2030, 1, 1))
        self._document(self.emp_asha, self.type_contract, date(2026, 1, 1))
        self._document(self.emp_asha, self.type_certificate, None)
        self.assertEqual(self.emp_asha.drkds_hr_document_count, 3)
        self.assertEqual(self.emp_asha.drkds_hr_expired_document_count, 1)
        self.assertEqual(self.emp_ravi.drkds_hr_document_count, 0)
        action = self.emp_asha.action_view_drkds_hr_documents()
        self.assertEqual(action["domain"], [("employee_id", "=", self.emp_asha.id)])
        self.assertEqual(action["context"]["default_employee_id"], self.emp_asha.id)

    def test_deleting_employee_deletes_documents(self):
        """The scans, the reminder, the chatter and the followers go with the
        documents, archived ones included; nothing is left keyed to them."""
        with freeze_time(TODAY):
            doc = self._document(self.emp_priya, self.type_passport, date(2026, 12, 1))
            archived = self._document(self.emp_priya, self.type_contract, date(2030, 1, 1))
            archived.action_archive()
            self.Document._cron_refresh_states()
        self.assertTrue(self._reminders(doc))
        doc_ids = (doc | archived).ids
        self.emp_priya.with_user(self.hr_officer).unlink()
        self.assertFalse((doc | archived).exists())
        for table, model_column in (
            ("ir_attachment", "res_model"),
            ("mail_activity", "res_model"),
            ("mail_message", "model"),
            ("mail_followers", "res_model"),
        ):
            self.env.cr.execute(
                f"SELECT count(*) FROM {table} WHERE {model_column} = %s AND res_id = ANY(%s)",  # noqa: S608
                ["drkds.hr.document", doc_ids],
            )
            self.assertEqual(self.env.cr.fetchone()[0], 0, table)

    def test_plain_user_cannot_delete_employee_documents(self):
        """The ORM clean-up runs in sudo, but only after the caller's own
        right to delete the employee is checked."""
        doc = self._document(self.emp_priya, self.type_passport, date(2030, 1, 1))
        with self.assertRaises(AccessError):
            self.emp_priya.with_user(self.plain_user).unlink()
        self.assertTrue(doc.exists())


@tagged("post_install", "-at_install")
class TestSecurity(DocumentExpiryCommon):
    def test_hr_officer_manages_documents_not_types(self):
        doc = self._document(self.emp_asha, self.type_passport, date(2030, 1, 1))
        officer_doc = doc.with_user(self.hr_officer)
        officer_doc.note = "Checked"
        self.assertEqual(officer_doc.read(["number"])[0]["number"], False)
        self.assertTrue(self.DocType.with_user(self.hr_officer).search([]))
        with self.assertRaises(AccessError):
            self.DocType.with_user(self.hr_officer).create({"name": "Nope"})
        self.DocType.with_user(self.hr_manager).create({"name": "Visa"})

    def test_plain_employee_sees_nothing(self):
        self._document(self.emp_asha, self.type_passport, date(2030, 1, 1))
        with self.assertRaises(AccessError):
            self.Document.with_user(self.plain_user).search([])
        with self.assertRaises(AccessError):
            self.DocType.with_user(self.plain_user).search([])

    def test_other_company_documents_hidden(self):
        other = self.env["res.company"].create({"name": "Other Co"})
        outsider = self._employee("Outsider", company_id=other.id)
        self.hr_officer.write({"company_ids": [(4, other.id)]})
        doc = self._document(outsider, self.type_passport, date(2030, 1, 1))
        self.assertEqual(doc.company_id, other)
        visible = self.Document.with_user(self.hr_officer).with_context(
            allowed_company_ids=[self.company.id]
        ).search([("id", "=", doc.id)])
        self.assertFalse(visible)
