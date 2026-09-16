from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestDrkdsBranch(AccountTestInvoicingCommon):
    """Behaviour tests for the branch field, its defaults, its record rules,
    its group-bys and its optional numbering."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Branch = cls.env["drkds.lite.branch"]
        cls.branch_blr = Branch.create({"name": "Bengaluru", "code": "blr"})
        cls.branch_mum = Branch.create({"name": "Mumbai", "code": "MUM"})

        cls.user_blr = cls._make_user("Counter Bengaluru", cls.branch_blr)
        cls.user_mum = cls._make_user("Counter Mumbai", cls.branch_mum)
        cls.user_hq = cls._make_user("Owner", None)

        cls.customer = cls.env["res.partner"].create({"name": "Walk-in Customer"})

    @classmethod
    def _make_user(cls, name, branch):
        # group_partner_manager is needed because these tests create contacts
        # as the counter user to prove the branch default applies on create.
        groups = cls.env.ref("base.group_user") \
            + cls.env.ref("base.group_partner_manager") \
            + cls.env.ref("account.group_account_invoice") \
            + cls.env.ref("sales_team.group_sale_salesman_all_leads")
        vals = {
            "name": name,
            "login": name.lower().replace(" ", "."),
            "company_id": cls.env.company.id,
            "company_ids": [Command.set(cls.env.company.ids)],
            "group_ids": [Command.set(groups.ids)],
        }
        if branch:
            vals["drkds_branch_id"] = branch.id
            vals["drkds_branch_ids"] = [Command.set(branch.ids)]
        return cls.env["res.users"].create(vals)

    def _invoice(self, branch, user=None, amount=100.0, post=True):
        env = self.env if user is None else self.env(user=user)
        move = env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.customer.id,
            "invoice_date": fields.Date.from_string("2026-03-05"),
            "drkds_branch_id": branch.id if branch else False,
            "invoice_line_ids": [Command.create({
                "name": "Service",
                "quantity": 1,
                "price_unit": amount,
                "tax_ids": [Command.clear()],
            })],
        })
        if post:
            move.action_post()
        return move

    # -- the branch record itself --------------------------------------
    def test_code_is_upper_cased_and_unique(self):
        """Codes are normalised on save and may not repeat in a company."""
        self.assertEqual(self.branch_blr.code, "BLR")
        self.assertEqual(self.branch_blr.display_name, "[BLR] Bengaluru")
        with self.assertRaises(Exception):
            with self.cr.savepoint():
                self.env["drkds.lite.branch"].create({"name": "Other", "code": "blr"})

    def test_code_rejects_punctuation(self):
        with self.assertRaises(ValidationError):
            self.env["drkds.lite.branch"].create({"name": "Bad", "code": "A B!"})

    # -- defaults from the user ----------------------------------------
    def test_default_branch_on_sale_order(self):
        """A sales order created by counter staff carries their branch."""
        order = self.env["sale.order"].with_user(self.user_blr).create({
            "partner_id": self.customer.id,
        })
        self.assertEqual(order.drkds_branch_id, self.branch_blr)

    def test_default_branch_on_invoice_and_partner(self):
        move = self.env["account.move"].with_user(self.user_mum).create({
            "move_type": "out_invoice",
            "partner_id": self.customer.id,
        })
        self.assertEqual(move.drkds_branch_id, self.branch_mum)
        partner = self.env["res.partner"].with_user(self.user_mum).create({"name": "New Lead"})
        self.assertEqual(partner.drkds_branch_id, self.branch_mum)

    def test_no_default_for_a_user_without_a_branch(self):
        """A user with no branch gets a blank branch, not a guessed one."""
        order = self.env["sale.order"].with_user(self.user_hq).create({
            "partner_id": self.customer.id,
        })
        self.assertFalse(order.drkds_branch_id)

    def test_single_allowed_branch_acts_as_the_default(self):
        """One allowed branch and no default is unambiguous, so it is used."""
        self.user_hq.write({"drkds_branch_ids": [Command.set(self.branch_mum.ids)]})
        self.assertEqual(self.user_hq._drkds_default_branch(), self.branch_mum)
        self.user_hq.write({"drkds_branch_ids": [Command.clear()]})

    def test_default_branch_must_be_an_allowed_branch(self):
        with self.assertRaises(ValidationError):
            self.user_blr.write({"drkds_branch_ids": [Command.set(self.branch_mum.ids)]})

    def test_sale_order_branch_flows_to_the_invoice(self):
        order = self.env["sale.order"].with_user(self.user_blr).create({
            "partner_id": self.customer.id,
            "order_line": [Command.create({
                "product_id": self.product_a.id,
                "product_uom_qty": 1,
            })],
        })
        order.sudo().action_confirm()
        invoice = order.sudo()._create_invoices()
        self.assertEqual(invoice.drkds_branch_id, self.branch_blr)

    # -- record rules ---------------------------------------------------
    def test_a_branch_user_cannot_see_another_branch_invoice(self):
        """The whole point: Bengaluru cannot read Mumbai's invoice."""
        mum_invoice = self._invoice(self.branch_mum)
        visible = self.env["account.move"].with_user(self.user_blr).search(
            [("id", "=", mum_invoice.id)]
        )
        self.assertFalse(visible, "Mumbai's invoice leaked into a Bengaluru search")
        with self.assertRaises(AccessError):
            mum_invoice.with_user(self.user_blr).read(["name"])

    def test_a_branch_user_sees_their_own_and_unassigned_invoices(self):
        blr_invoice = self._invoice(self.branch_blr)
        orphan_invoice = self._invoice(None)
        visible = self.env["account.move"].with_user(self.user_blr).search(
            [("id", "in", (blr_invoice + orphan_invoice).ids)]
        )
        self.assertEqual(visible, blr_invoice + orphan_invoice)

    def test_a_user_without_a_branch_sees_every_branch(self):
        """Documented behaviour: no branch assigned means no restriction."""
        moves = self._invoice(self.branch_blr) + self._invoice(self.branch_mum)
        visible = self.env["account.move"].with_user(self.user_hq).search(
            [("id", "in", moves.ids)]
        )
        self.assertEqual(visible, moves)

    def test_the_rule_also_covers_sales_orders(self):
        order = self.env["sale.order"].with_user(self.user_mum).create({
            "partner_id": self.customer.id,
        })
        found = self.env["sale.order"].with_user(self.user_blr).search(
            [("id", "=", order.id)]
        )
        self.assertFalse(found)

    def test_contacts_are_labelled_not_hidden(self):
        """Contacts stay readable across branches - shared master data."""
        partner = self.env["res.partner"].create({
            "name": "Mumbai Regular", "drkds_branch_id": self.branch_mum.id,
        })
        self.assertTrue(
            self.env["res.partner"].with_user(self.user_blr).search([("id", "=", partner.id)])
        )

    # -- reporting ------------------------------------------------------
    def test_group_by_branch_returns_correct_totals(self):
        self._invoice(self.branch_blr, amount=100.0)
        self._invoice(self.branch_blr, amount=250.0)
        self._invoice(self.branch_mum, amount=400.0)
        groups = self.env["account.move"]._read_group(
            domain=[
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("drkds_branch_id", "!=", False),
            ],
            groupby=["drkds_branch_id"],
            aggregates=["amount_total:sum"],
        )
        totals = {branch.id: total for branch, total in groups}
        self.assertEqual(totals[self.branch_blr.id], 350.0)
        self.assertEqual(totals[self.branch_mum.id], 400.0)

    # -- optional branch numbering --------------------------------------
    def test_branch_numbering_is_off_by_default(self):
        first = self._invoice(self.branch_blr)
        self.assertNotIn("BLR", first.name)

    def test_two_branches_number_independently(self):
        """With the switch on, each branch runs its own series in one journal."""
        self.env.company.drkds_branch_invoice_sequence = True
        blr_one = self._invoice(self.branch_blr)
        mum_one = self._invoice(self.branch_mum)
        blr_two = self._invoice(self.branch_blr)

        self.assertIn("-BLR/", blr_one.name)
        self.assertIn("-MUM/", mum_one.name)
        self.assertEqual(blr_one.journal_id, mum_one.journal_id)
        # Each branch starts at 1 and advances on its own.
        self.assertTrue(blr_one.name.endswith("00001"), blr_one.name)
        self.assertTrue(mum_one.name.endswith("00001"), mum_one.name)
        self.assertTrue(blr_two.name.endswith("00002"), blr_two.name)
