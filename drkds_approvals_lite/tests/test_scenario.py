"""End to end: a clerk raises two expense claims, the approver approves one
and refuses the other, and the manager sees both without being involved."""
from odoo.tests import Form, tagged

from .common import ApprovalsCommon


@tagged("post_install", "-at_install")
class TestApprovalScenario(ApprovalsCommon):
    def test_clerk_raises_two_requests(self):
        clerk_env = self.env(user=self.clerk)

        # 1. Clerk fills in two claims through the form, as a user would.
        f = Form(clerk_env["drkds.approval.request"])
        f.title = "Taxi to client site"
        f.category_id = self.cat_expense
        f.amount = 1250.0
        f.description = "<p>Two return trips to the Andheri office.</p>"
        taxi = f.save()

        f = Form(clerk_env["drkds.approval.request"])
        f.title = "Team lunch"
        f.category_id = self.cat_expense
        f.amount = 4800.0
        f.description = "<p>Lunch for six after the release.</p>"
        lunch = f.save()

        self.assertEqual(taxi.requester_id, self.clerk, "the form defaults the requester")
        self.assertEqual(taxi.state, "draft")
        self.assertEqual(taxi.currency_id, self.env.company.currency_id)
        self.assertNotEqual(taxi.name, lunch.name)
        self.assertEqual(int(lunch.name[4:]) - int(taxi.name[4:]), 1)

        # 2. Submit both: two approvers in the category, so 2 to-dos each.
        taxi.action_submit()
        lunch.action_submit()
        self.assertEqual((taxi | lunch).mapped("state"), ["submitted", "submitted"])
        self.assertEqual(len(self._todo_activities(taxi)), 2)
        self.assertEqual(len(self._todo_activities(lunch)), 2)

        # 3. The approver's "To Approve" list shows exactly these two.
        to_approve = self.Request.with_user(self.approver).search([
            ("state", "=", "submitted"),
            ("approver_ids", "in", self.approver.id),
            ("requester_id", "!=", self.approver.id),
        ])
        self.assertEqual(to_approve, taxi | lunch)

        # 4. Approve the taxi, refuse the lunch through the wizard.
        taxi.with_user(self.approver).action_approve()
        wizard = self.env["drkds.approval.refuse.wizard"].with_user(self.approver).create({
            "request_id": lunch.id,
            "reason": "Entertainment is not claimable this quarter.",
        })
        wizard.action_refuse()

        self.assertEqual(taxi.state, "approved")
        self.assertEqual(taxi.approver_id, self.approver)
        self.assertTrue(taxi.decision_date)
        self.assertEqual(lunch.state, "refused")
        self.assertEqual(lunch.refusal_reason, "Entertainment is not claimable this quarter.")
        self.assertEqual(lunch.approver_id, self.approver)

        # Both decisions cleared every pending to-do, for both approvers.
        self.assertEqual(len(self._todo_activities(taxi)), 0)
        self.assertEqual(len(self._todo_activities(lunch)), 0)

        # 5. The requester was told by a chatter message addressed to them.
        taxi_bodies = " ".join(taxi.message_ids.mapped("body"))
        lunch_bodies = " ".join(lunch.message_ids.mapped("body"))
        self.assertIn("approved", taxi_bodies)
        self.assertIn("refused", lunch_bodies)
        self.assertIn("Entertainment is not claimable", lunch_bodies)
        #    (Odoo 19 keeps recipients as notifications on the message.)
        self.assertIn(self.clerk.partner_id, taxi.message_ids.notification_ids.mapped("res_partner_id"))
        self.assertIn(self.clerk.partner_id, lunch.message_ids.notification_ids.mapped("res_partner_id"))

        # 6. The clerk sees both, so does the manager, the outsider sees none,
        #    and the expense total is 1250 + 4800 = 6050.
        domain = [("id", "in", (taxi | lunch).ids)]
        self.assertEqual(self.Request.with_user(self.clerk).search_count(domain), 2)
        self.assertEqual(self.Request.with_user(self.manager).search_count(domain), 2)
        self.assertEqual(self.Request.with_user(self.outsider).search_count(domain), 0)
        self.assertEqual(sum(self.Request.with_user(self.manager).search(domain).mapped("amount")), 6050.0)

        # 7. Nothing can be decided twice; the second approver finds nothing left.
        self.assertFalse(taxi.with_user(self.approver_2).can_decide)
        self.assertFalse(lunch.with_user(self.approver_2).can_decide)
        self.assertEqual(self.cat_expense.request_count, 2)
