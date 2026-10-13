from psycopg2 import IntegrityError

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import ApprovalsCommon


@tagged("post_install", "-at_install")
class TestApprovalRequest(ApprovalsCommon):
    # -- numbering -----------------------------------------------------
    def test_reference_is_sequential_and_unique(self):
        """Three requests take three consecutive APR/ numbers."""
        requests = self.Request.with_user(self.clerk).create([
            {"title": "A", "category_id": self.cat_leave.id},
            {"title": "B", "category_id": self.cat_leave.id},
            {"title": "C", "category_id": self.cat_leave.id},
        ])
        names = requests.mapped("name")
        self.assertEqual(len(set(names)), 3)
        for name in names:
            self.assertRegex(name, r"^APR/\d{5}$")
        tails = [int(name.split("/")[1]) for name in names]
        self.assertEqual(tails[1] - tails[0], 1)
        self.assertEqual(tails[2] - tails[1], 1)

    def test_copy_takes_a_fresh_reference_and_resets_decision(self):
        request = self._request(self.clerk)
        request.with_user(self.clerk).action_submit()
        request.with_user(self.approver).action_approve()
        copy = request.with_user(self.clerk).copy()
        self.assertNotEqual(copy.name, request.name)
        self.assertNotEqual(copy.name, "/")
        self.assertEqual(copy.state, "draft")
        self.assertFalse(copy.approver_id)
        self.assertFalse(copy.decision_date)

    def test_display_name_joins_reference_and_title(self):
        request = self._request(self.clerk, title="Taxi fares")
        self.assertEqual(request.display_name, f"{request.name} Taxi fares")

    # -- category requirements on submit -------------------------------
    def test_submit_needs_description_when_required(self):
        request = self._request(self.clerk, description=False)
        with self.assertRaises(ValidationError):
            request.with_user(self.clerk).action_submit()
        self.assertEqual(request.state, "draft")

    def test_submit_needs_amount_when_required(self):
        request = self._request(self.clerk, amount=0.0)
        with self.assertRaises(ValidationError):
            request.with_user(self.clerk).action_submit()

    def test_submit_needs_partner_when_required(self):
        request = self._request(self.clerk, category_id=self.cat_purchase.id, partner_id=False)
        with self.assertRaises(ValidationError):
            request.with_user(self.clerk).action_submit()
        request.partner_id = self.supplier
        request.with_user(self.clerk).action_submit()
        self.assertEqual(request.state, "submitted")

    def test_leave_needs_no_amount(self):
        """Leave of absence only requires a description; amount 0 is fine."""
        request = self._request(self.clerk, category_id=self.cat_leave.id, amount=0.0)
        request.with_user(self.clerk).action_submit()
        self.assertEqual(request.state, "submitted")

    def test_submit_refused_when_category_has_no_approver(self):
        self.cat_leave.approver_ids = [(5, 0, 0)]
        request = self._request(self.clerk, category_id=self.cat_leave.id)
        with self.assertRaises(UserError):
            request.with_user(self.clerk).action_submit()

    def test_negative_amount_rejected(self):
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            self._request(self.clerk, amount=-1.0)

    # -- activities ----------------------------------------------------
    def test_submit_schedules_one_todo_per_approver(self):
        """Expense claim has two approvers, so submit creates exactly 2 activities."""
        request = self._request(self.clerk)
        self.assertEqual(len(self._todo_activities(request)), 0)
        request.with_user(self.clerk).action_submit()
        activities = self._todo_activities(request)
        self.assertEqual(len(activities), 2)
        self.assertEqual(set(activities.mapped("user_id.id")), {self.approver.id, self.approver_2.id})

    def test_decision_clears_the_other_approvers_todo(self):
        request = self._request(self.clerk)
        request.with_user(self.clerk).action_submit()
        request.with_user(self.approver).action_approve()
        self.assertEqual(len(self._todo_activities(request)), 0)

    def test_cancel_clears_todos(self):
        request = self._request(self.clerk)
        request.with_user(self.clerk).action_submit()
        request.with_user(self.clerk).action_cancel()
        self.assertEqual(request.state, "cancelled")
        self.assertEqual(len(self._todo_activities(request)), 0)

    # -- deciding ------------------------------------------------------
    def test_approve_records_who_and_when(self):
        request = self._request(self.clerk)
        request.with_user(self.clerk).action_submit()
        self.assertFalse(request.approver_id)
        request.with_user(self.approver).action_approve()
        self.assertEqual(request.state, "approved")
        self.assertEqual(request.approver_id, self.approver)
        self.assertTrue(request.decision_date)
        self.assertFalse(request.refusal_reason)

    def test_approve_posts_the_approved_mail(self):
        request = self._request(self.clerk)
        request.with_user(self.clerk).action_submit()
        before = len(request.message_ids)
        request.with_user(self.approver).action_approve()
        new_messages = request.message_ids[: len(request.message_ids) - before]
        bodies = " ".join(new_messages.mapped("body"))
        self.assertIn("approved", bodies)
        self.assertIn(request.name, bodies)
        # Odoo 19 records recipients as notifications, not on message.partner_ids
        self.assertIn(self.clerk.partner_id, new_messages.notification_ids.mapped("res_partner_id"))

    def test_refuse_needs_a_reason(self):
        request = self._request(self.clerk)
        request.with_user(self.clerk).action_submit()
        with self.assertRaises(ValidationError):
            request.with_user(self.approver).action_refuse("")
        with self.assertRaises(ValidationError):
            request.with_user(self.approver).action_refuse("   ")
        self.assertEqual(request.state, "submitted")

    def test_refuse_through_wizard(self):
        request = self._request(self.clerk)
        request.with_user(self.clerk).action_submit()
        action = request.with_user(self.approver).action_open_refuse_wizard()
        self.assertEqual(action["res_model"], "drkds.approval.refuse.wizard")
        wizard = self.env["drkds.approval.refuse.wizard"].with_user(self.approver).with_context(
            action["context"]
        ).create({"reason": "No receipts attached."})
        self.assertEqual(wizard.request_id, request)
        wizard.action_refuse()
        self.assertEqual(request.state, "refused")
        self.assertEqual(request.refusal_reason, "No receipts attached.")
        self.assertEqual(request.approver_id, self.approver)
        bodies = " ".join(request.message_ids.mapped("body"))
        self.assertIn("No receipts attached.", bodies)

    def test_requester_cannot_approve_own_request_even_as_approver(self):
        """The approver raises a request in a category they approve: still no."""
        request = self._request(self.approver)
        request.with_user(self.approver).action_submit()
        with self.assertRaises(UserError):
            request.with_user(self.approver).action_approve()
        with self.assertRaises(UserError):
            request.with_user(self.approver).action_refuse("Nope")
        self.assertEqual(request.state, "submitted")
        # the other approver can
        request.with_user(self.approver_2).action_approve()
        self.assertEqual(request.state, "approved")

    def test_manager_cannot_approve_own_request(self):
        request = self._request(self.manager)
        request.with_user(self.manager).action_submit()
        with self.assertRaises(UserError):
            request.with_user(self.manager).action_approve()

    def test_non_approver_cannot_decide(self):
        """A user with read access through another path still may not decide."""
        request = self._request(self.clerk)
        request.with_user(self.clerk).action_submit()
        # requester is not an approver
        with self.assertRaises(UserError):
            request.with_user(self.clerk).action_approve()
        self.assertFalse(request.with_user(self.clerk).can_decide)
        self.assertTrue(request.with_user(self.approver).can_decide)

    def test_manager_may_decide_on_others_requests(self):
        request = self._request(self.clerk)
        request.with_user(self.clerk).action_submit()
        self.assertTrue(request.with_user(self.manager).can_decide)
        request.with_user(self.manager).action_refuse("Budget frozen.")
        self.assertEqual(request.state, "refused")
        self.assertEqual(request.approver_id, self.manager)

    # -- state machine -------------------------------------------------
    def test_cannot_decide_on_draft(self):
        request = self._request(self.clerk)
        with self.assertRaises(UserError):
            request.with_user(self.approver).action_approve()

    def test_cannot_decide_twice(self):
        request = self._request(self.clerk)
        request.with_user(self.clerk).action_submit()
        request.with_user(self.approver).action_approve()
        with self.assertRaises(UserError):
            request.with_user(self.approver_2).action_refuse("Too late")
        self.assertEqual(request.approver_id, self.approver)

    def test_submit_only_from_draft(self):
        request = self._request(self.clerk)
        request.with_user(self.clerk).action_submit()
        with self.assertRaises(UserError):
            request.with_user(self.clerk).action_submit()

    def test_cancel_only_when_open(self):
        request = self._request(self.clerk)
        request.with_user(self.clerk).action_submit()
        request.with_user(self.approver).action_approve()
        with self.assertRaises(UserError):
            request.with_user(self.clerk).action_cancel()

    def test_cancel_by_stranger_refused(self):
        request = self._request(self.clerk)
        request.with_user(self.clerk).action_submit()
        with self.assertRaises(UserError):
            request.with_user(self.approver).action_cancel()
        request.with_user(self.manager).action_cancel()
        self.assertEqual(request.state, "cancelled")

    def test_reset_to_draft_clears_the_decision(self):
        request = self._request(self.clerk)
        request.with_user(self.clerk).action_submit()
        request.with_user(self.approver).action_refuse("Missing receipt.")
        request.with_user(self.clerk).action_reset_to_draft()
        self.assertEqual(request.state, "draft")
        self.assertFalse(request.approver_id)
        self.assertFalse(request.decision_date)
        self.assertFalse(request.refusal_reason)
        # and it can go round again
        request.with_user(self.clerk).action_submit()
        request.with_user(self.approver).action_approve()
        self.assertEqual(request.state, "approved")

    def test_reset_only_from_refused_or_cancelled(self):
        request = self._request(self.clerk)
        request.with_user(self.clerk).action_submit()
        request.with_user(self.approver).action_approve()
        with self.assertRaises(UserError):
            request.with_user(self.clerk).action_reset_to_draft()

    def test_delete_only_draft_or_cancelled(self):
        request = self._request(self.clerk)
        request.with_user(self.clerk).action_submit()
        with self.assertRaises(UserError):
            request.with_user(self.manager).unlink()
        request.with_user(self.clerk).action_cancel()
        request.with_user(self.manager).unlink()
        self.assertFalse(request.exists())

    # -- record rules --------------------------------------------------
    def test_user_sees_own_and_approvable_only(self):
        """clerk: 2 own. approver: 2 expense (approves) + 1 leave (approves) = 3.
        approver_2: 2 expense only. outsider: 0. manager: all 3."""
        r1 = self._request(self.clerk)
        r2 = self._request(self.clerk, title="Hotel")
        r3 = self._request(self.manager, category_id=self.cat_leave.id)
        ids = (r1 | r2 | r3).ids
        domain = [("id", "in", ids)]
        self.assertEqual(self.Request.with_user(self.clerk).search_count(domain), 2)
        self.assertEqual(self.Request.with_user(self.approver).search_count(domain), 3)
        self.assertEqual(self.Request.with_user(self.approver_2).search_count(domain), 2)
        self.assertEqual(self.Request.with_user(self.outsider).search_count(domain), 0)
        self.assertEqual(self.Request.with_user(self.manager).search_count(domain), 3)
        with self.assertRaises(AccessError):
            r1.with_user(self.outsider).read(["title"])

    def test_user_cannot_delete_or_edit_categories(self):
        with self.assertRaises(AccessError):
            self.cat_leave.with_user(self.clerk).write({"name": "X"})
        with self.assertRaises(AccessError):
            self._request(self.clerk).with_user(self.clerk).unlink()

    def test_category_request_count(self):
        self._request(self.clerk)
        self._request(self.clerk)
        self._request(self.clerk, category_id=self.cat_leave.id)
        self.assertEqual(self.cat_expense.request_count, 2)
        self.assertEqual(self.cat_leave.request_count, 1)
        self.assertEqual(self.cat_purchase.request_count, 0)
