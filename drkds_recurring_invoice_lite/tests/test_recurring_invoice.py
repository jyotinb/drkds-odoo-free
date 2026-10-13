from datetime import date
from unittest.mock import patch

from freezegun import freeze_time
from psycopg2.errors import CheckViolation

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestRecurringInvoice(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Template = cls.env["drkds.recurring.invoice"]
        cls.Move = cls.env["account.move"]
        cls.tax_18 = cls.env["account.tax"].create({
            "name": "RCL Test 18%",
            "amount_type": "percent",
            "amount": 18.0,
            "type_tax_use": "sale",
            "company_id": cls.company_data["company"].id,
        })

    def _template(self, **vals):
        """A running-ready template: 3 x 1000 taxed 18% plus 2 x 250 untaxed.

        Untaxed 3000 + 500 = 3500; tax 18% of 3000 = 540; total 4040.
        """
        base = {
            "name": "Unit test template",
            "partner_id": self.partner_a.id,
            "next_date": date(2026, 1, 15),
            "interval_number": 1,
            "interval_unit": "month",
            "line_ids": [
                Command.create({
                    "product_id": self.product_a.id,
                    "name": "Taxed service",
                    "quantity": 3.0,
                    "price_unit": 1000.0,
                    "tax_ids": [Command.set(self.tax_18.ids)],
                }),
                Command.create({
                    "name": "Untaxed extra",
                    "quantity": 2.0,
                    "price_unit": 250.0,
                    "tax_ids": [Command.clear()],
                }),
            ],
        }
        base.update(vals)
        return self.Template.create(base)

    # -- date arithmetic ------------------------------------------------
    def test_month_end_anchor(self):
        adv = self.Template._advance_date
        # 31 Jan + 1 month clamps to the last day of February...
        feb = adv(date(2026, 1, 31), 1, "month", anchor_day=31)
        self.assertEqual(feb, date(2026, 2, 28))
        # ...and with the anchor kept, March returns to the 31st.
        self.assertEqual(adv(feb, 1, "month", anchor_day=31), date(2026, 3, 31))
        # Without an anchor the day decays, which is why the anchor exists.
        self.assertEqual(adv(feb, 1, "month"), date(2026, 3, 28))
        # Quarterly from 30 November: 28 February (leap-free 2026), then 30 May.
        q1 = adv(date(2025, 11, 30), 3, "month", anchor_day=30)
        self.assertEqual(q1, date(2026, 2, 28))
        self.assertEqual(adv(q1, 3, "month", anchor_day=30), date(2026, 5, 30))

    def test_leap_year_anchor(self):
        adv = self.Template._advance_date
        y1 = adv(date(2024, 2, 29), 1, "year", anchor_day=29)
        self.assertEqual(y1, date(2025, 2, 28))
        # 2028 is a leap year again: the 29th comes back.
        self.assertEqual(adv(date(2024, 2, 29), 4, "year", anchor_day=29), date(2028, 2, 29))
        self.assertEqual(adv(y1, 3, "year", anchor_day=29), date(2028, 2, 29))

    def test_day_and_week_intervals(self):
        adv = self.Template._advance_date
        self.assertEqual(adv(date(2026, 1, 30), 3, "day"), date(2026, 2, 2))
        self.assertEqual(adv(date(2026, 1, 30), 2, "week"), date(2026, 2, 13))
        self.assertEqual(adv(date(2026, 12, 31), 1, "day"), date(2027, 1, 1))
        with self.assertRaises(ValueError):
            adv(date(2026, 1, 1), 0, "day")
        with self.assertRaises(ValueError):
            adv(date(2026, 1, 1), 1, "fortnight")

    def test_anchor_follows_user_edits_only(self):
        tpl = self._template(next_date=date(2026, 1, 31))
        self.assertEqual(tpl.anchor_day, 31)
        tpl.action_start()
        with freeze_time("2026-01-31"):
            tpl._cron_generate_invoices()
        self.assertEqual(tpl.next_date, date(2026, 2, 28))
        self.assertEqual(tpl.anchor_day, 31, "the scheduler must not re-anchor")
        tpl.next_date = date(2026, 4, 15)
        self.assertEqual(tpl.anchor_day, 15, "a user edit re-anchors")

    # -- generation ------------------------------------------------------
    def test_totals_with_tax(self):
        tpl = self._template()
        self.assertEqual(tpl.amount_untaxed, 3500.0)
        self.assertEqual(tpl.amount_tax, 540.0)
        self.assertEqual(tpl.amount_total, 4040.0)
        tpl.action_start()
        tpl.action_generate_now()
        invoice = tpl.invoice_ids
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.move_type, "out_invoice")
        self.assertEqual(invoice.state, "draft")
        self.assertEqual(invoice.invoice_date, date(2026, 1, 15))
        self.assertEqual(invoice.partner_id, self.partner_a)
        self.assertEqual(invoice.recurring_id, tpl)
        self.assertEqual(invoice.invoice_origin, tpl.reference)
        self.assertEqual(invoice.amount_untaxed, 3500.0)
        self.assertEqual(invoice.amount_tax, 540.0)
        self.assertEqual(invoice.amount_total, 4040.0)
        self.assertEqual(len(invoice.invoice_line_ids), 2)
        self.assertEqual(tpl.last_invoice_date, date(2026, 1, 15))
        self.assertEqual(tpl.invoice_count, 1)
        self.assertEqual(tpl.next_date, date(2026, 2, 15))

    def test_cron_creates_exactly_one(self):
        tpl = self._template()
        tpl.action_start()
        with freeze_time("2026-01-15"):
            created = tpl._cron_generate_invoices()
            self.assertEqual(len(created), 1)
            # A second run on the same day finds nothing due.
            self.assertFalse(tpl._cron_generate_invoices())
        self.assertEqual(tpl.invoice_count, 1)
        self.assertEqual(tpl.next_date, date(2026, 2, 15))
        # Before the due date nothing happens for a template; the job is
        # model-level and still serves the others that are due.
        other = self._template(next_date=date(2026, 3, 1))
        other.action_start()
        with freeze_time("2026-02-28"):
            created = self.Template._cron_generate_invoices()
        self.assertEqual(created.recurring_id, tpl, "only the February one of tpl")
        self.assertEqual(created.invoice_date, date(2026, 2, 15))
        self.assertEqual(other.invoice_count, 0)

    def test_idempotent_per_date(self):
        tpl = self._template()
        tpl.action_start()
        tpl.action_generate_now()
        # The user drags the date back to one already invoiced.
        tpl.next_date = date(2026, 1, 15)
        with freeze_time("2026-01-20"):
            tpl._cron_generate_invoices()
        self.assertEqual(tpl.invoice_count, 1, "never two invoices for one date")
        self.assertEqual(tpl.next_date, date(2026, 2, 15))
        # Generate Now on an already-invoiced date opens the existing invoice.
        tpl.next_date = date(2026, 1, 15)
        action = tpl.action_generate_now()
        self.assertEqual(action["res_id"], tpl.invoice_ids.id)
        self.assertEqual(tpl.invoice_count, 1)
        # A cancelled invoice does not block the date: it is reissued.
        tpl.invoice_ids.button_cancel()
        tpl.next_date = date(2026, 1, 15)
        tpl.action_generate_now()
        self.assertEqual(len(tpl.invoice_ids), 2)
        self.assertEqual(tpl.invoice_count, 1, "cancelled invoices are not counted")

    def test_catch_up_after_downtime(self):
        tpl = self._template(next_date=date(2026, 1, 5), interval_unit="week")
        tpl.action_start()
        with freeze_time("2026-01-26"):
            created = tpl._cron_generate_invoices()
        self.assertEqual(len(created), 4)
        self.assertEqual(
            sorted(created.mapped("invoice_date")),
            [date(2026, 1, 5), date(2026, 1, 12), date(2026, 1, 19), date(2026, 1, 26)],
        )
        self.assertEqual(tpl.next_date, date(2026, 2, 2))

    def test_done_at_end_date(self):
        tpl = self._template(end_date=date(2026, 3, 15))
        tpl.action_start()
        with freeze_time("2026-04-01"):
            created = tpl._cron_generate_invoices()
        self.assertEqual(len(created), 3)
        self.assertEqual(tpl.state, "done")
        self.assertEqual(tpl.next_date, date(2026, 4, 15))
        self.assertEqual(tpl.last_invoice_date, date(2026, 3, 15))
        # Nothing more comes out of a finished template.
        with freeze_time("2026-05-01"):
            self.assertFalse(tpl._cron_generate_invoices())
        self.assertEqual(tpl.invoice_count, 3)

    def test_auto_post(self):
        tpl = self._template(auto_post=True)
        tpl.action_start()
        with freeze_time("2026-01-15"):
            tpl._cron_generate_invoices()
        self.assertEqual(tpl.invoice_ids.state, "posted")
        self.assertEqual(tpl.invoice_ids.amount_residual, 4040.0)

    def test_cron_isolates_a_failing_template(self):
        """A posting refused for one template must not stop the others.

        Posting is made to fail deterministically; only the auto-posted
        template reaches it, the other stays in draft and is served.
        """
        bad = self._template(name="Bad", auto_post=True)
        good = self._template(name="Good")
        (bad + good).action_start()

        def refuse(moves):
            raise UserError("Posting refused for the test")

        with freeze_time("2026-01-15"), mute_logger(
            "odoo.addons.drkds_recurring_invoice_lite.models.drkds_recurring_invoice"
        ), patch.object(type(self.Move), "action_post", refuse):
            created = self.Template._cron_generate_invoices()
        self.assertIn("Posting refused", bad.last_error)
        self.assertEqual(created.recurring_id, good)
        self.assertTrue(bad.last_error)
        self.assertEqual(bad.next_date, date(2026, 1, 15), "a failed template is retried")
        self.assertFalse(bad.invoice_ids)
        self.assertFalse(good.last_error)

    # -- workflow and guards ---------------------------------------------
    def test_workflow(self):
        tpl = self._template()
        self.assertTrue(tpl.reference.startswith("REC/"))
        self.assertEqual(tpl.display_name, f"{tpl.reference} Unit test template")
        with self.assertRaises(UserError):
            tpl.action_generate_now()
        with self.assertRaises(UserError):
            tpl.action_pause()
        tpl.action_start()
        self.assertEqual(tpl.state, "running")
        tpl.action_pause()
        self.assertEqual(tpl.state, "paused")
        with freeze_time("2026-02-20"):
            self.assertFalse(tpl._cron_generate_invoices(), "paused templates are skipped")
        tpl.action_start()
        self.assertEqual(tpl.state, "running")
        tpl.action_done()
        self.assertEqual(tpl.state, "done")
        tpl.action_draft()
        self.assertEqual(tpl.state, "draft")

    def test_start_needs_a_real_line(self):
        tpl = self._template(line_ids=[
            Command.create({"display_type": "line_section", "name": "Heading"}),
        ])
        with self.assertRaises(UserError):
            tpl.action_start()

    def test_end_before_next_rejected(self):
        with self.assertRaises(ValidationError):
            self._template(next_date=date(2026, 3, 1), end_date=date(2026, 2, 1))

    def test_interval_must_be_positive(self):
        with self.assertRaises(CheckViolation), mute_logger("odoo.sql_db"):
            self._template(interval_number=0)

    def test_unlink_keeps_trail(self):
        tpl = self._template()
        tpl.action_start()
        tpl.action_generate_now()
        with self.assertRaises(UserError):
            tpl.unlink()
        empty = self._template()
        empty.unlink()
        self.assertFalse(empty.exists())

    def test_copy(self):
        tpl = self._template(next_date=date(2026, 1, 31))
        tpl.action_start()
        tpl.action_generate_now()
        dup = tpl.copy()
        self.assertEqual(dup.state, "draft")
        self.assertNotEqual(dup.reference, tpl.reference)
        self.assertEqual(len(dup.line_ids), 2)
        self.assertEqual(dup.amount_total, 4040.0)
        self.assertFalse(dup.invoice_ids)
