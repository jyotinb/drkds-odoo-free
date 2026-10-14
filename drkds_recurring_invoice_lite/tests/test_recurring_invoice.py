from datetime import date
from unittest.mock import patch

from freezegun import freeze_time
from psycopg2.errors import CheckViolation

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, new_test_user, tagged
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
    def test_board_columns_follow_the_workflow(self):
        """The kanban groups templates by status. Its columns came in
        alphabetical order (Done, Draft, Paused, Running), which reads the
        workflow backwards. Every status now has its column, in workflow order."""
        running = self._template()
        running.action_start()
        self._template()
        result = self.Template.with_context(read_group_expand=True).web_read_group(
            [("id", "in", (running | self.Template.search([], order="id desc", limit=1)).ids)],
            ["state"], ["__count"])
        columns = [(group["state"], group["__count"]) for group in result["groups"]]
        self.assertEqual(columns, [("draft", 1), ("running", 1), ("paused", 0), ("done", 0)])

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
        with self.assertRaises(ValidationError):
            tpl.action_start()
        self.assertEqual(tpl.state, "draft")

    def test_running_needs_lines_whatever_the_path(self):
        """The rules Start applies hold for direct writes and creates too
        (RPC, imports, a default_state in the context): otherwise the
        scheduler would issue an empty invoice every period."""
        bare = {"name": "Bare", "partner_id": self.partner_a.id, "next_date": date(2026, 1, 15)}
        with self.assertRaises(ValidationError):
            self.Template.create(dict(bare, state="running"))
        with self.assertRaises(ValidationError):
            self.Template.with_context(default_state="running").create(bare)
        tpl = self._template()
        tpl.action_start()
        with self.assertRaises(ValidationError):
            tpl.write({"line_ids": [Command.clear()]})
        closed = self._template(end_date=date(2026, 1, 15))
        closed.action_start()
        closed.action_generate_now()
        with self.assertRaises(ValidationError):
            closed.write({"state": "running"})
        self.assertEqual(closed.state, "done")

    def test_generation_ignores_default_keys_in_context(self):
        """Defaults meant for the template (default_state) must not reach
        the invoice it creates."""
        tpl = self._template()
        tpl.action_start()
        action = tpl.with_context(default_state="running", default_name="X/1").action_generate_now()
        invoice = self.Move.browse(action["res_id"])
        self.assertEqual(invoice.state, "draft")
        self.assertNotEqual(invoice.name, "X/1")
        self.assertEqual(invoice.amount_total, 4040.0)

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

    def test_start_refused_past_end_date(self):
        """A template closed by its end date and reset to draft cannot run on
        until its dates are put right."""
        tpl = self._template(end_date=date(2026, 1, 15))
        tpl.action_start()
        tpl.action_generate_now()
        self.assertEqual(tpl.state, "done")
        self.assertEqual(tpl.next_date, date(2026, 2, 15))
        tpl.action_draft()
        with self.assertRaises(ValidationError):
            tpl.action_start()
        self.assertEqual(tpl.state, "draft")
        tpl.end_date = date(2026, 6, 30)
        tpl.action_start()
        self.assertEqual(tpl.state, "running")

    def test_journal_must_be_a_sale_journal(self):
        tpl = self._template()
        with self.assertRaises(ValidationError):
            tpl.journal_id = self.company_data["default_journal_purchase"]

    def test_anchor_taken_from_default_next_date(self):
        """Created without a next date (import, API), the template is
        anchored on the default date, today, like the form would do."""
        with freeze_time("2026-01-31"):
            tpl = self.Template.create({
                "name": "Imported",
                "partner_id": self.partner_a.id,
                "line_ids": [Command.create({"name": "Fee", "price_unit": 100.0})],
            })
        self.assertEqual(tpl.next_date, date(2026, 1, 31))
        self.assertEqual(tpl.anchor_day, 31)
        self.assertEqual(tpl._next_after(date(2026, 2, 28)), date(2026, 3, 31))

    # -- what the invoice carries -----------------------------------------
    def test_fiscal_position_maps_taxes(self):
        """An export customer's fiscal position replaces 18% by 0%, as it
        would on an invoice typed by hand.

        Lines: 3 x 1000 at 18% (mapped to 0%) + 2 x 250 untaxed.
        Untaxed 3500, tax 0, total 3500 (and not 4040).
        """
        company = self.company_data["company"]
        tax_0 = self.env["account.tax"].create({
            "name": "RCL Export 0%",
            "amount_type": "percent",
            "amount": 0.0,
            "type_tax_use": "sale",
            "company_id": company.id,
            "original_tax_ids": [Command.set(self.tax_18.ids)],
        })
        export = self.env["account.fiscal.position"].create({
            "name": "RCL Export",
            "company_id": company.id,
            "tax_ids": [Command.set(tax_0.ids)],
        })
        customer = self.env["res.partner"].create({
            "name": "RCL Overseas Buyer",
            "property_account_position_id": export.id,
        })
        tpl = self._template(partner_id=customer.id)
        tpl.action_start()
        tpl.action_generate_now()
        invoice = tpl.invoice_ids
        self.assertEqual(invoice.fiscal_position_id, export)
        taxed = invoice.invoice_line_ids.filtered(lambda l: l.name == "Taxed service")
        self.assertEqual(taxed.tax_ids, tax_0)
        self.assertEqual(invoice.amount_untaxed, 3500.0)
        self.assertEqual(invoice.amount_tax, 0.0)
        self.assertEqual(invoice.amount_total, 3500.0)
        # A customer without a fiscal position keeps the template's taxes.
        plain = self._template()
        plain.action_start()
        plain.action_generate_now()
        self.assertEqual(plain.invoice_ids.amount_total, 4040.0)

    def test_foreign_currency_template(self):
        """product_a lists at 1000 USD (company currency). From 2017 the test
        rate is 2 EUR per USD, so a EUR template prices it 2000 EUR:
        untaxed 2000, tax 18% 360, total 2360 EUR = 1180 USD."""
        eur = self.setup_other_currency("EUR")
        f = Form(self.Template)
        f.name = "Euro retainer"
        f.partner_id = self.partner_a
        f.next_date = date(2026, 1, 15)
        f.currency_id = eur
        with f.line_ids.new() as line:
            line.product_id = self.product_a
            line.tax_ids.clear()
            line.tax_ids.add(self.tax_18)
        tpl = f.save()
        self.assertEqual(tpl.line_ids.price_unit, 2000.0)
        self.assertEqual(tpl.amount_total, 2360.0)
        tpl.action_start()
        tpl.action_generate_now()
        invoice = tpl.invoice_ids
        self.assertEqual(invoice.currency_id, eur)
        self.assertEqual(invoice.amount_total, 2360.0)
        self.assertEqual(invoice.amount_total_signed, 1180.0)

    def test_payment_terms_and_conditions(self):
        """The customer's payment terms come onto the template; the company's
        default terms and conditions stay on the invoice unless the template
        has its own; an invoice without terms is due on its own date."""
        company = self.company_data["company"]
        terms_30 = self.env.ref("account.account_payment_term_30days")
        self.env["ir.config_parameter"].sudo().set_param("account.use_invoice_terms", True)
        company.invoice_terms = "<p>Goods once sold are not taken back.</p>"
        customer = self.env["res.partner"].create({
            "name": "RCL Thirty Days",
            "property_payment_term_id": terms_30.id,
        })
        f = Form(self.Template)
        f.name = "Thirty days"
        f.partner_id = customer
        f.next_date = date(2026, 1, 15)
        with f.line_ids.new() as line:
            line.name = "Service"
            line.price_unit = 1000.0
        tpl = f.save()
        self.assertEqual(tpl.payment_term_id, terms_30)
        tpl.action_start()
        tpl.action_generate_now()
        invoice = tpl.invoice_ids
        self.assertEqual(invoice.invoice_payment_term_id, terms_30)
        self.assertEqual(invoice.invoice_date_due, date(2026, 2, 14))
        self.assertIn("Goods once sold", invoice.narration)
        # The template's own conditions replace the company default.
        tpl.narration = "<p>Payable by NEFT only.</p>"
        tpl.action_generate_now()
        second = tpl.invoice_ids - invoice
        self.assertIn("NEFT", second.narration)
        self.assertNotIn("Goods once sold", second.narration)
        # No terms anywhere: issued ahead of time, still due on its own date.
        bare = self.env["res.partner"].create({"name": "RCL No Terms"})
        early = self._template(partner_id=bare.id, next_date=date(2026, 3, 1))
        self.assertFalse(early.payment_term_id)
        with freeze_time("2026-02-10"):
            early.action_start()
            early.action_generate_now()
        self.assertEqual(early.invoice_ids.invoice_date, date(2026, 3, 1))
        self.assertEqual(early.invoice_ids.invoice_date_due, date(2026, 3, 1))

    # -- companies, users and time zones -----------------------------------
    def test_branch_uses_parent_journal_and_taxes(self):
        """A branch has no journals or taxes of its own; it invoices on its
        parent's, like any invoice typed in the branch. product_a: 1000 at
        the parent's 15% sale tax, total 1150."""
        company = self.company_data["company"]
        branch = self._create_company(name="RCL Branch", parent_id=company.id)
        f = Form(self.Template.with_company(branch))
        f.name = "Branch retainer"
        f.partner_id = self.partner_a
        f.next_date = date(2026, 1, 15)
        self.assertEqual(f.journal_id, self.company_data["default_journal_sale"])
        with f.line_ids.new() as line:
            line.product_id = self.product_a
        tpl = f.save()
        self.assertEqual(tpl.company_id, branch)
        self.assertEqual(tpl.line_ids.tax_ids, self.tax_sale_a)
        self.assertEqual(tpl.amount_total, 1150.0)
        tpl.action_start()
        tpl.action_generate_now()
        invoice = tpl.invoice_ids
        self.assertEqual(invoice.company_id, branch)
        self.assertEqual(invoice.journal_id, self.company_data["default_journal_sale"])
        self.assertEqual(invoice.amount_total, 1150.0)

    def test_cron_serves_every_company_whatever_its_user(self):
        """The scheduled action may be pointed at a user with no accounting
        rights; it still serves every company, each invoice in its own."""
        tpl = self._template()
        other = self.setup_other_company(name="RCL Second Company")
        tpl2 = self.Template.with_company(other["company"]).create({
            "name": "Second company",
            "partner_id": self.partner_a.id,
            "company_id": other["company"].id,
            "next_date": date(2026, 1, 15),
            "line_ids": [Command.create({"name": "Fee", "quantity": 1.0, "price_unit": 100.0})],
        })
        (tpl + tpl2).action_start()
        bot = new_test_user(self.env, login="rcl_cron", groups="base.group_user")
        with freeze_time("2026-01-15 06:00:00"):
            created = self.Template.with_user(bot)._cron_generate_invoices()
        self.assertEqual(len(created), 2)
        self.assertEqual(tpl.invoice_ids.company_id, self.company_data["company"])
        self.assertEqual(tpl2.invoice_ids.company_id, other["company"])
        self.assertEqual(tpl2.invoice_ids.journal_id, other["default_journal_sale"])
        self.assertEqual(tpl2.invoice_ids.amount_total, 100.0)

    def test_today_is_read_in_the_salesperson_time_zone(self):
        """23:30 UTC on 14 January is already 05:00 on the 15th in India and
        still the 14th in New York (18:30)."""
        def owner(login, tz):
            return new_test_user(
                self.env, login=login, tz=tz,
                groups="base.group_user,account.group_account_invoice",
            )
        ist = self._template(name="Kolkata", user_id=owner("rcl_ist", "Asia/Kolkata").id)
        nyc = self._template(name="New York", user_id=owner("rcl_nyc", "America/New_York").id)
        (ist + nyc).action_start()
        with freeze_time("2026-01-14 23:30:00"):
            created = self.Template._cron_generate_invoices()
        self.assertEqual(created.recurring_id, ist)
        self.assertEqual(created.invoice_date, date(2026, 1, 15))
        self.assertEqual(nyc.next_date, date(2026, 1, 15))
        # 05:30 UTC on the 15th is 00:30 in New York: its turn.
        with freeze_time("2026-01-15 05:30:00"):
            created = self.Template._cron_generate_invoices()
        self.assertEqual(created.recurring_id, nyc)

    def test_invoice_readers_without_template_access(self):
        """A user who may read invoices but not templates (a salesperson)
        does not get the template field on the invoice form or search, so
        neither can reach a model they cannot read."""
        reader_group = self.env["res.groups"].create({"name": "RCL invoice reader"})
        self.env["ir.model.access"].create({
            "name": "rcl invoice reader",
            "model_id": self.env.ref("account.model_account_move").id,
            "group_id": reader_group.id,
            "perm_read": True,
        })
        reader = new_test_user(
            self.env, login="rcl_reader",
            group_ids=(self.env.ref("base.group_user") | reader_group).ids,
        )
        form = self.env.ref("account.view_move_form").id
        search = self.env.ref("account.view_account_invoice_filter").id
        views = self.env["account.move"].with_user(reader).get_views([(form, "form"), (search, "search")])
        self.assertNotIn("recurring_id", views["views"]["form"]["arch"])
        self.assertNotIn("recurring_id", views["views"]["search"]["arch"])
        billing = new_test_user(
            self.env, login="rcl_billing", groups="base.group_user,account.group_account_invoice",
        )
        views = self.env["account.move"].with_user(billing).get_views([(form, "form"), (search, "search")])
        self.assertIn("recurring_id", views["views"]["form"]["arch"])
        self.assertIn("recurring_id", views["views"]["search"]["arch"])

    def test_read_only_users_get_no_action_buttons(self):
        readonly = new_test_user(
            self.env, login="rcl_readonly", groups="base.group_user,account.group_account_readonly",
        )
        arch = self.Template.with_user(readonly).get_views([(False, "form")])["views"]["form"]["arch"]
        for button in ("action_start", "action_pause", "action_generate_now", "action_done", "action_draft"):
            self.assertNotIn(f'name="{button}"', arch)
        self.assertIn('name="action_view_invoices"', arch)
