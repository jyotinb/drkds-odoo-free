from odoo.tests import TransactionCase, new_test_user


class ApprovalsCommon(TransactionCase):
    """Three people: a clerk who raises requests, an approver who decides on
    the Expense claim category, and a manager who sees everything."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Request = cls.env["drkds.approval.request"]
        cls.Category = cls.env["drkds.approval.category"]

        cls.clerk = new_test_user(
            cls.env, login="drkds_apl_clerk", name="Clerk",
            groups="base.group_user,drkds_approvals_lite.group_approval_user",
        )
        cls.approver = new_test_user(
            cls.env, login="drkds_apl_approver", name="Approver",
            groups="base.group_user,drkds_approvals_lite.group_approval_user",
        )
        cls.approver_2 = new_test_user(
            cls.env, login="drkds_apl_approver_2", name="Second Approver",
            groups="base.group_user,drkds_approvals_lite.group_approval_user",
        )
        cls.manager = new_test_user(
            cls.env, login="drkds_apl_manager", name="Manager",
            groups="base.group_user,drkds_approvals_lite.group_approval_manager",
        )
        cls.outsider = new_test_user(
            cls.env, login="drkds_apl_outsider", name="Outsider",
            groups="base.group_user,drkds_approvals_lite.group_approval_user",
        )

        cls.cat_expense = cls.env.ref("drkds_approvals_lite.category_expense_claim")
        cls.cat_leave = cls.env.ref("drkds_approvals_lite.category_leave_of_absence")
        cls.cat_purchase = cls.env.ref("drkds_approvals_lite.category_purchase_need")
        cls.cat_expense.approver_ids = [(6, 0, (cls.approver | cls.approver_2).ids)]
        cls.cat_leave.approver_ids = [(6, 0, cls.approver.ids)]
        cls.cat_purchase.approver_ids = [(6, 0, cls.approver.ids)]

        # An outside party: it may sit on a request as its contact, and must
        # never be mailed the internal decision.
        cls.supplier = cls.env["res.partner"].create(
            {"name": "Sharma Stationers", "email": "sales@sharmastationers.example"}
        )

    def _request(self, user, **vals):
        values = {
            "title": "Taxi fares",
            "category_id": self.cat_expense.id,
            "description": "<p>Client visit, two trips.</p>",
            "amount": 850.0,
        }
        values.update(vals)
        return self.Request.with_user(user).create(values)

    def _todo_activities(self, request):
        return self.env["mail.activity"].search([
            ("res_model", "=", "drkds.approval.request"),
            ("res_id", "=", request.id),
        ])

    def _notified_partners(self, request, before_message_ids):
        """Partners notified (inbox or email) by the messages posted on
        `request` since `before_message_ids` was taken."""
        messages = request.message_ids.filtered(lambda m: m.id not in before_message_ids)
        return messages.notification_ids.res_partner_id
