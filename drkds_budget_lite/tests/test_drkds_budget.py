from psycopg2 import IntegrityError

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestDrkdsBudget(TransactionCase):
    """Behaviour tests for budget actuals, signs, variance and isolation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Budget Co"})
        cls.other_company = cls.env["res.company"].create({"name": "Other Budget Co"})
        cls.env.user.company_ids |= cls.company | cls.other_company
        cls.env.user.company_id = cls.company
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=cls.company.ids))

        cls.Account = cls.env["account.account"].with_company(cls.company)
        cls.expense_account = cls.Account.create({
            "name": "Travel Expense",
            "code": "600100",
            "account_type": "expense",
            "company_ids": [Command.set(cls.company.ids)],
        })
        cls.expense_account_2 = cls.Account.create({
            "name": "Hotel Expense",
            "code": "600200",
            "account_type": "expense",
            "company_ids": [Command.set(cls.company.ids)],
        })
        cls.income_account = cls.Account.create({
            "name": "Service Income",
            "code": "400100",
            "account_type": "income",
            "company_ids": [Command.set(cls.company.ids)],
        })
        cls.counterpart = cls.Account.create({
            "name": "Budget Counterpart",
            "code": "100100",
            "account_type": "asset_current",
            "company_ids": [Command.set(cls.company.ids)],
        })
        cls.journal = cls.env["account.journal"].create({
            "name": "Budget Misc",
            "code": "BMSC",
            "type": "general",
            "company_id": cls.company.id,
        })

        cls.date_from = fields.Date.to_date("2026-04-01")
        cls.date_to = fields.Date.to_date("2026-06-30")

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    @classmethod
    def _make_move(cls, account, amount, date, post=True, analytic=None):
        """One balanced entry: `amount` debited to `account`, credited to cash.

        A negative amount therefore credits `account`, which is how income is
        recorded.
        """
        line_vals = {"account_id": account.id, "balance": amount}
        if analytic is not None:
            line_vals["analytic_distribution"] = analytic
        move = cls.env["account.move"].create({
            "journal_id": cls.journal.id,
            "date": date,
            "company_id": cls.company.id,
            "line_ids": [
                Command.create(line_vals),
                Command.create({"account_id": cls.counterpart.id, "balance": -amount}),
            ],
        })
        if post:
            move.action_post()
        return move

    def _make_budget(self, lines, company=None, **kwargs):
        vals = {
            "name": kwargs.pop("name", "Test Budget"),
            "date_from": kwargs.pop("date_from", self.date_from),
            "date_to": kwargs.pop("date_to", self.date_to),
            "company_id": (company or self.company).id,
            "line_ids": [Command.create(line) for line in lines],
        }
        vals.update(kwargs)
        return self.env["drkds.budget"].create(vals)

    # ------------------------------------------------------------------
    # actuals: period, posting state and account selection
    # ------------------------------------------------------------------
    def test_actual_counts_only_posted_entries_in_period(self):
        """Only posted items dated inside the period feed the actual."""
        self._make_move(self.expense_account, 1000.0, "2026-05-10")
        self._make_move(self.expense_account, 500.0, "2026-04-01")   # first day, in
        self._make_move(self.expense_account, 700.0, "2026-06-30")   # last day, in
        self._make_move(self.expense_account, 9999.0, "2026-03-31")  # before, out
        self._make_move(self.expense_account, 8888.0, "2026-07-01")  # after, out
        budget = self._make_budget([
            {"account_id": self.expense_account.id, "planned_amount": 5000.0},
        ])
        self.assertEqual(budget.line_ids.actual_amount, 2200.0)

    def test_draft_entry_is_excluded(self):
        """A draft journal entry must not move the actual."""
        budget = self._make_budget([
            {"account_id": self.expense_account.id, "planned_amount": 5000.0},
        ])
        self.assertEqual(budget.line_ids.actual_amount, 0.0)
        draft = self._make_move(self.expense_account, 1234.0, "2026-05-10", post=False)
        budget.line_ids.invalidate_recordset()
        self.assertEqual(draft.state, "draft")
        self.assertEqual(
            budget.line_ids.actual_amount, 0.0,
            "A draft entry leaked into the budget actual.",
        )
        draft.action_post()
        budget.line_ids.invalidate_recordset()
        self.assertEqual(budget.line_ids.actual_amount, 1234.0)

    def test_actual_ignores_other_accounts(self):
        """Spend on a different account does not touch the line."""
        self._make_move(self.expense_account, 300.0, "2026-05-10")
        self._make_move(self.expense_account_2, 700.0, "2026-05-10")
        budget = self._make_budget([
            {"account_id": self.expense_account.id, "planned_amount": 1000.0},
        ])
        self.assertEqual(budget.line_ids.actual_amount, 300.0)

    # ------------------------------------------------------------------
    # sign convention
    # ------------------------------------------------------------------
    def test_expense_sign_convention(self):
        """An expense debit raises the actual as a positive amount."""
        self._make_move(self.expense_account, 1200.0, "2026-05-10")
        budget = self._make_budget([
            {"account_id": self.expense_account.id, "planned_amount": 1000.0},
        ])
        line = budget.line_ids
        self.assertEqual(line.budget_direction, "expense")
        self.assertEqual(line.actual_amount, 1200.0)

    def test_income_sign_convention(self):
        """Income is stored as a credit and must still read positive."""
        self._make_move(self.income_account, -1500.0, "2026-05-10")
        budget = self._make_budget([
            {"account_id": self.income_account.id, "planned_amount": 1000.0},
        ])
        line = budget.line_ids
        self.assertEqual(line.budget_direction, "income")
        self.assertEqual(
            line.actual_amount, 1500.0,
            "Income actual came out negative; the sign flip is missing.",
        )

    def test_income_credit_note_reduces_actual(self):
        """A debit on an income account reduces collections, not raises them."""
        self._make_move(self.income_account, -1500.0, "2026-05-10")
        self._make_move(self.income_account, 200.0, "2026-05-11")
        budget = self._make_budget([
            {"account_id": self.income_account.id, "planned_amount": 1000.0},
        ])
        self.assertEqual(budget.line_ids.actual_amount, 1300.0)

    # ------------------------------------------------------------------
    # variance
    # ------------------------------------------------------------------
    def test_expense_under_budget_is_favourable(self):
        self._make_move(self.expense_account, 800.0, "2026-05-10")
        budget = self._make_budget([
            {"account_id": self.expense_account.id, "planned_amount": 1000.0},
        ])
        line = budget.line_ids
        self.assertEqual(line.variance_amount, 200.0)
        self.assertEqual(line.variance_percent, 20.0)
        self.assertEqual(line.achieved_percent, 80.0)
        self.assertFalse(line.is_over_budget)

    def test_expense_over_budget_is_flagged(self):
        self._make_move(self.expense_account, 1250.0, "2026-05-10")
        budget = self._make_budget([
            {"account_id": self.expense_account.id, "planned_amount": 1000.0},
        ])
        line = budget.line_ids
        self.assertEqual(line.variance_amount, -250.0)
        self.assertEqual(line.variance_percent, -25.0)
        self.assertTrue(line.is_over_budget)

    def test_income_under_collection_is_over_budget(self):
        """Under-collection on an income line is the unfavourable case."""
        self._make_move(self.income_account, -600.0, "2026-05-10")
        budget = self._make_budget([
            {"account_id": self.income_account.id, "planned_amount": 1000.0},
        ])
        line = budget.line_ids
        self.assertEqual(line.variance_amount, -400.0)
        self.assertEqual(line.variance_percent, -40.0)
        self.assertTrue(line.is_over_budget)

    def test_income_over_collection_is_favourable(self):
        self._make_move(self.income_account, -1400.0, "2026-05-10")
        budget = self._make_budget([
            {"account_id": self.income_account.id, "planned_amount": 1000.0},
        ])
        line = budget.line_ids
        self.assertEqual(line.variance_amount, 400.0)
        self.assertFalse(line.is_over_budget)

    def test_zero_planned_line_does_not_divide_by_zero(self):
        """A nil budget is legal: percentages report zero, nothing raises."""
        self._make_move(self.expense_account, 500.0, "2026-05-10")
        budget = self._make_budget([
            {"account_id": self.expense_account.id, "planned_amount": 0.0},
        ])
        line = budget.line_ids
        self.assertEqual(line.actual_amount, 500.0)
        self.assertEqual(line.variance_amount, -500.0)
        self.assertEqual(line.variance_percent, 0.0)
        self.assertEqual(line.achieved_percent, 0.0)
        self.assertTrue(line.is_over_budget)
        self.assertEqual(budget.variance_percent, 0.0)

    def test_document_totals_add_up(self):
        self._make_move(self.expense_account, 800.0, "2026-05-10")
        self._make_move(self.income_account, -1400.0, "2026-05-10")
        budget = self._make_budget([
            {"account_id": self.expense_account.id, "planned_amount": 1000.0},
            {"account_id": self.income_account.id, "planned_amount": 1000.0},
        ])
        self.assertEqual(budget.planned_total, 2000.0)
        self.assertEqual(budget.actual_total, 2200.0)
        self.assertEqual(budget.variance_total, 600.0)  # +200 expense, +400 income
        self.assertEqual(budget.variance_percent, 30.0)
        self.assertEqual(budget.over_budget_line_count, 0)

    # ------------------------------------------------------------------
    # account groups and analytic
    # ------------------------------------------------------------------
    def test_account_group_covers_every_account_in_range(self):
        group = self.env["account.group"].create({
            "name": "Travel and Hotel",
            "code_prefix_start": "6001",
            "code_prefix_end": "6002",
            "company_id": self.company.id,
        })
        self._make_move(self.expense_account, 300.0, "2026-05-10")
        self._make_move(self.expense_account_2, 700.0, "2026-05-10")
        self._make_move(self.income_account, -900.0, "2026-05-10")
        budget = self._make_budget([
            {"account_group_id": group.id, "planned_amount": 1500.0},
        ])
        line = budget.line_ids
        self.assertEqual(
            set(line.account_ids.ids),
            {self.expense_account.id, self.expense_account_2.id},
        )
        self.assertEqual(line.actual_amount, 1000.0)
        self.assertEqual(line.variance_amount, 500.0)

    def test_analytic_line_counts_only_its_share(self):
        analytic_plan = self.env["account.analytic.plan"].create({"name": "Budget Plan"})
        analytic = self.env["account.analytic.account"].create({
            "name": "Project B",
            "plan_id": analytic_plan.id,
            "company_id": self.company.id,
        })
        other_analytic = self.env["account.analytic.account"].create({
            "name": "Project C",
            "plan_id": analytic_plan.id,
            "company_id": self.company.id,
        })
        self._make_move(
            self.expense_account, 1000.0, "2026-05-10",
            analytic={str(analytic.id): 40.0, str(other_analytic.id): 60.0},
        )
        self._make_move(self.expense_account, 500.0, "2026-05-11")  # no analytic
        budget = self._make_budget([
            {
                "account_id": self.expense_account.id,
                "analytic_account_id": analytic.id,
                "planned_amount": 1000.0,
            },
        ])
        self.assertEqual(budget.line_ids.actual_amount, 400.0)

    # ------------------------------------------------------------------
    # drill-down
    # ------------------------------------------------------------------
    def test_drill_down_returns_exactly_the_underlying_items(self):
        inside = self._make_move(self.expense_account, 300.0, "2026-05-10")
        self._make_move(self.expense_account, 400.0, "2026-01-10")  # outside period
        budget = self._make_budget([
            {"account_id": self.expense_account.id, "planned_amount": 1000.0},
        ])
        action = budget.line_ids.action_open_move_lines()
        self.assertEqual(action["res_model"], "account.move.line")
        found = self.env["account.move.line"].search(action["domain"])
        expected = inside.line_ids.filtered(lambda l: l.account_id == self.expense_account)
        self.assertEqual(found, expected)

    # ------------------------------------------------------------------
    # document rules
    # ------------------------------------------------------------------
    def test_line_needs_an_account_or_a_group(self):
        with self.assertRaises(ValidationError):
            self._make_budget([{"planned_amount": 100.0}])

    def test_line_refuses_account_and_group_together(self):
        group = self.env["account.group"].create({
            "name": "Sixes", "code_prefix_start": "6", "code_prefix_end": "6",
            "company_id": self.company.id,
        })
        with self.assertRaises(ValidationError):
            self._make_budget([{
                "account_id": self.expense_account.id,
                "account_group_id": group.id,
                "planned_amount": 100.0,
            }])

    def test_period_must_not_be_reversed(self):
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            with self.env.cr.savepoint():
                self._make_budget(
                    [{"account_id": self.expense_account.id, "planned_amount": 1.0}],
                    date_from=self.date_to, date_to=self.date_from,
                )

    def test_empty_budget_cannot_be_confirmed(self):
        budget = self._make_budget([])
        with self.assertRaises(UserError):
            budget.action_confirm()

    def test_state_flow(self):
        budget = self._make_budget([
            {"account_id": self.expense_account.id, "planned_amount": 100.0},
        ])
        self.assertEqual(budget.state, "draft")
        budget.action_confirm()
        self.assertEqual(budget.state, "confirmed")
        budget.action_done()
        self.assertEqual(budget.state, "done")
        with self.assertRaises(UserError):
            budget.action_cancel()
        budget.action_draft()
        budget.action_cancel()
        self.assertEqual(budget.state, "cancel")

    def test_period_is_locked_once_in_force(self):
        budget = self._make_budget([
            {"account_id": self.expense_account.id, "planned_amount": 100.0},
        ])
        budget.action_confirm()
        with self.assertRaises(UserError):
            budget.date_to = fields.Date.to_date("2026-12-31")
        budget.action_draft()
        budget.date_to = fields.Date.to_date("2026-12-31")
        self.assertEqual(budget.date_to, fields.Date.to_date("2026-12-31"))

    # ------------------------------------------------------------------
    # multi-company
    # ------------------------------------------------------------------
    def test_company_rule_isolates_budgets(self):
        """A user allowed only in one company never sees the other's budgets."""
        mine = self._make_budget(
            [{"account_id": self.expense_account.id, "planned_amount": 100.0}],
            name="Mine",
        )
        theirs = self.env["drkds.budget"].create({
            "name": "Theirs",
            "date_from": self.date_from,
            "date_to": self.date_to,
            "company_id": self.other_company.id,
        })
        reader = new_test_user(
            self.env, login="budget_reader",
            groups="account.group_account_user",
            company_id=self.company.id,
            company_ids=[Command.set(self.company.ids)],
        )
        visible = self.env["drkds.budget"].with_user(reader).search([])
        self.assertIn(mine, visible)
        self.assertNotIn(theirs, visible)
        with self.assertRaises(AccessError):
            theirs.with_user(reader).read(["name"])

    def test_line_company_follows_the_budget(self):
        budget = self._make_budget(
            [{"account_id": self.expense_account.id, "planned_amount": 100.0}],
        )
        self.assertEqual(budget.line_ids.company_id, self.company)

    def test_account_of_another_company_is_refused(self):
        foreign = self.env["account.account"].with_company(self.other_company).create({
            "name": "Foreign Expense",
            "code": "600900",
            "account_type": "expense",
            "company_ids": [Command.set(self.other_company.ids)],
        })
        with self.assertRaises(ValidationError):
            self._make_budget([{"account_id": foreign.id, "planned_amount": 100.0}])

    def test_actual_ignores_other_company_entries(self):
        """Even the same account code in another company must not leak in."""
        budget = self._make_budget([
            {"account_id": self.expense_account.id, "planned_amount": 1000.0},
        ])
        self._make_move(self.expense_account, 250.0, "2026-05-10")
        budget.line_ids.invalidate_recordset()
        self.assertEqual(budget.line_ids.actual_amount, 250.0)
        domain = budget.line_ids._get_move_line_domain()
        self.assertIn(("company_id", "=", self.company.id), domain)
