from psycopg2 import IntegrityError

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import QualityCase


@tagged("post_install", "-at_install")
class TestQualityCheck(QualityCase):

    # -- control points ------------------------------------------------
    def test_point_needs_a_product_or_a_category(self):
        with self.assertRaises(ValidationError):
            self.Point.create({"name": "Nothing to match"})

    def test_measure_point_rejects_inverted_range(self):
        with self.assertRaises(ValidationError):
            self.Point.create({
                "name": "Bad range", "product_id": self.steel.id,
                "check_type": "measure", "norm_min": 5, "norm_max": 1,
            })

    @mute_logger("odoo.sql_db")
    def test_point_title_is_unique_per_company(self):
        self.Point.create({"name": "Visual", "product_id": self.steel.id})
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self.Point.create({"name": "Visual", "product_id": self.copper.id})

    def test_point_that_raised_checks_cannot_be_deleted(self):
        """Deleting a point must not take its inspection records with it:
        refused once it has raised a check, allowed before."""
        used = self.Point.create({"name": "Visual", "product_id": self.steel.id})
        unused = self.Point.create({"name": "Never used", "product_id": self.copper.id})
        picking = self._picking(self.receipt_type, [(self.steel, 1)])
        picking.action_confirm()
        check = picking.drkds_quality_check_ids
        check.action_fail()
        with self.assertRaises(UserError):
            used.unlink()
        self.assertTrue(used.exists())
        self.assertTrue(check.exists())
        self.assertEqual(check.state, "fail")
        unused.unlink()
        self.assertFalse(unused.exists())

    # -- creation on confirmation --------------------------------------
    def test_one_check_per_matching_move(self):
        """Point on the raw category; receipt of steel (sub-category),
        copper (category) and tape (other category): 2 checks, not 3."""
        point = self.Point.create({
            "name": "Visual on receipt", "product_category_id": self.categ_raw.id,
        })
        picking = self._picking(self.receipt_type, [
            (self.steel, 10), (self.copper, 5), (self.tape, 20),
        ])
        self.assertFalse(picking.drkds_quality_check_ids, "nothing before confirmation")
        picking.action_confirm()
        checks = picking.drkds_quality_check_ids
        self.assertEqual(len(checks), 2)
        self.assertEqual(checks.mapped("product_id"), self.steel | self.copper)
        self.assertEqual(checks.mapped("point_id"), point)
        self.assertEqual(set(checks.mapped("state")), {"todo"})
        for check in checks:
            self.assertEqual(check.move_id.picking_id, picking)
            self.assertRegex(check.name, r"^QC/\d{5}$")
        self.assertEqual(picking.drkds_quality_check_count, 2)
        self.assertEqual(picking.drkds_quality_open_count, 2)

    def test_product_point_matches_only_that_product(self):
        self.Point.create({"name": "Steel only", "product_id": self.steel.id})
        picking = self._picking(self.receipt_type, [(self.steel, 1), (self.copper, 1)])
        picking.action_confirm()
        self.assertEqual(picking.drkds_quality_check_ids.product_id, self.steel)

    def test_point_limited_to_an_operation_type(self):
        """Receipt-only point: a delivery of the same product raises nothing."""
        self.Point.create({
            "name": "Receipt only", "product_id": self.steel.id,
            "picking_type_ids": [(6, 0, self.receipt_type.ids)],
        })
        self._put_in_stock(self.steel, 10)
        delivery = self._picking(self.delivery_type, [(self.steel, 2)])
        delivery.action_confirm()
        self.assertFalse(delivery.drkds_quality_check_ids)
        receipt = self._picking(self.receipt_type, [(self.steel, 2)])
        receipt.action_confirm()
        self.assertEqual(len(receipt.drkds_quality_check_ids), 1)

    def test_confirming_twice_raises_nothing_new(self):
        self.Point.create({"name": "Visual", "product_id": self.steel.id})
        picking = self._picking(self.receipt_type, [(self.steel, 1)])
        picking.action_confirm()
        picking.action_confirm()
        picking.move_ids._action_confirm()
        self.assertEqual(len(picking.drkds_quality_check_ids), 1)

    def test_archived_point_raises_nothing(self):
        self.Point.create({"name": "Old", "product_id": self.steel.id, "active": False})
        picking = self._picking(self.receipt_type, [(self.steel, 1)])
        picking.action_confirm()
        self.assertFalse(picking.drkds_quality_check_ids)

    def test_move_added_to_confirmed_picking_is_checked(self):
        self.Point.create({"name": "Visual", "product_category_id": self.categ_raw.id})
        picking = self._picking(self.receipt_type, [(self.steel, 1)])
        picking.action_confirm()
        self.assertEqual(len(picking.drkds_quality_check_ids), 1)
        move = self.env["stock.move"].create({
            "picking_id": picking.id,
            "product_id": self.copper.id,
            "product_uom_qty": 3,
            "product_uom": self.copper.uom_id.id,
            "location_id": picking.location_id.id,
            "location_dest_id": picking.location_dest_id.id,
        })
        move._action_confirm()
        self.assertEqual(len(picking.drkds_quality_check_ids), 2)

    def test_cancelled_move_drops_its_open_check_and_keeps_decided_ones(self):
        self.Point.create({"name": "Visual", "product_category_id": self.categ_raw.id})
        picking = self._picking(self.receipt_type, [(self.steel, 1), (self.copper, 1)])
        picking.action_confirm()
        steel_check = picking.drkds_quality_check_ids.filtered(lambda c: c.product_id == self.steel)
        steel_check.action_pass()
        picking.action_cancel()
        remaining = self.Check.search([("picking_id", "=", picking.id)])
        self.assertEqual(remaining, steel_check)

    # -- deciding ------------------------------------------------------
    def test_pass_records_user_and_date(self):
        self.Point.create({"name": "Visual", "product_id": self.steel.id})
        picking = self._picking(self.receipt_type, [(self.steel, 1)])
        picking.action_confirm()
        check = picking.drkds_quality_check_ids
        check.action_pass()
        self.assertEqual(check.state, "pass")
        self.assertEqual(check.user_id, self.env.user)
        self.assertTrue(check.date)
        check.action_reset_todo()
        self.assertEqual(check.state, "todo")
        self.assertFalse(check.user_id)
        self.assertFalse(check.date)
        check.action_fail()
        self.assertEqual(check.state, "fail")

    def test_a_decided_check_is_not_decided_again(self):
        """Two inspectors on the same check: the second click must not
        overwrite the first decision. Changing a result goes through Reset
        to To Do, which the chatter records."""
        stock_user = self.env.ref("stock.group_stock_user")
        first, second = self.env["res.users"].create([
            {"name": "Inspector One", "login": "qc.one", "group_ids": [Command.set(stock_user.ids)]},
            {"name": "Inspector Two", "login": "qc.two", "group_ids": [Command.set(stock_user.ids)]},
        ])
        self.Point.create({"name": "Visual", "product_id": self.steel.id})
        picking = self._picking(self.receipt_type, [(self.steel, 1)])
        picking.action_confirm()
        check = picking.drkds_quality_check_ids
        check.with_user(first).action_pass()
        decided_on = check.date
        for method in ("action_pass", "action_fail"):
            with self.assertRaises(UserError):
                getattr(check.with_user(second), method)()
        self.assertEqual(check.state, "pass")
        self.assertEqual(check.user_id, first)
        self.assertEqual(check.date, decided_on)
        check.with_user(second).action_reset_todo()
        check.with_user(second).action_fail()
        self.assertEqual(check.state, "fail")
        self.assertEqual(check.user_id, second)

    def test_a_recorded_measure_is_not_recorded_again(self):
        """Range 1.8 to 2.2: 2.0 passes; typing 2.5 over it and pressing
        Record Measure again is refused, the check stays passed until it is
        reset, after which 2.5 fails."""
        self.Point.create({
            "name": "Thickness", "product_id": self.steel.id,
            "check_type": "measure", "norm_min": 1.8, "norm_max": 2.2,
        })
        picking = self._picking(self.receipt_type, [(self.steel, 1)])
        picking.action_confirm()
        check = picking.drkds_quality_check_ids
        check.measure = 2.0
        check.action_measure()
        self.assertEqual(check.state, "pass")
        check.measure = 2.5
        with self.assertRaises(UserError):
            check.action_measure()
        self.assertEqual(check.state, "pass")
        check.action_reset_todo()
        check.action_measure()
        self.assertEqual(check.state, "fail")

    def test_measure_out_of_range_fails_and_in_range_passes(self):
        """Range 1.8 to 2.2 mm: 2.5 fails, 1.7 fails, 2.2 (boundary) passes,
        2.0 passes."""
        self.Point.create({
            "name": "Thickness", "product_id": self.steel.id,
            "check_type": "measure", "norm_min": 1.8, "norm_max": 2.2,
            "measure_unit": "mm",
        })
        picking = self._picking(self.receipt_type, [(self.steel, 1)])
        picking.action_confirm()
        check = picking.drkds_quality_check_ids
        self.assertEqual(check.measure_unit, "mm")
        for value, expected in [(2.5, "fail"), (1.7, "fail"), (2.2, "pass"), (2.0, "pass")]:
            check.action_reset_todo()
            check.measure = value
            check.action_measure()
            self.assertEqual(check.state, expected, "measure %s" % value)

    def test_measure_check_refuses_the_pass_fail_buttons(self):
        self.Point.create({
            "name": "Thickness", "product_id": self.steel.id,
            "check_type": "measure", "norm_min": 1, "norm_max": 2,
        })
        picking = self._picking(self.receipt_type, [(self.steel, 1)])
        picking.action_confirm()
        check = picking.drkds_quality_check_ids
        with self.assertRaises(UserError):
            check.action_pass()
        with self.assertRaises(UserError):
            check.action_fail()

    def test_pass_fail_check_refuses_record_measure(self):
        self.Point.create({"name": "Visual", "product_id": self.steel.id})
        picking = self._picking(self.receipt_type, [(self.steel, 1)])
        picking.action_confirm()
        with self.assertRaises(UserError):
            picking.drkds_quality_check_ids.action_measure()

    # -- the gate ------------------------------------------------------
    def test_blocking_todo_check_refuses_validation(self):
        self.Point.create({"name": "Visual", "product_id": self.steel.id})
        picking = self._picking(self.receipt_type, [(self.steel, 4)])
        picking.action_confirm()
        with self.assertRaises(UserError):
            self._validate(picking)
        self.assertNotEqual(picking.state, "done")

    def test_blocking_failed_check_refuses_validation(self):
        self.Point.create({"name": "Visual", "product_id": self.steel.id})
        picking = self._picking(self.receipt_type, [(self.steel, 4)])
        picking.action_confirm()
        picking.drkds_quality_check_ids.action_fail()
        with self.assertRaises(UserError):
            self._validate(picking)
        self.assertNotEqual(picking.state, "done")

    def test_passed_check_lets_validation_through(self):
        self.Point.create({"name": "Visual", "product_id": self.steel.id})
        picking = self._picking(self.receipt_type, [(self.steel, 4)])
        picking.action_confirm()
        picking.drkds_quality_check_ids.action_pass()
        self._validate(picking)
        self.assertEqual(picking.state, "done")
        self.assertEqual(picking.drkds_quality_open_count, 0)

    def test_non_blocking_point_lets_validation_through(self):
        """A non-blocking point records the result but never holds the goods:
        to-do and failed alike validate."""
        self.Point.create({
            "name": "Advisory look", "product_id": self.steel.id, "blocking": False,
        })
        todo = self._picking(self.receipt_type, [(self.steel, 1)])
        todo.action_confirm()
        self.assertEqual(len(todo.drkds_quality_check_ids), 1)
        self._validate(todo)
        self.assertEqual(todo.state, "done")

        failed = self._picking(self.receipt_type, [(self.steel, 1)])
        failed.action_confirm()
        failed.drkds_quality_check_ids.action_fail()
        self._validate(failed)
        self.assertEqual(failed.state, "done")
        self.assertEqual(failed.drkds_quality_check_ids.state, "fail")

    def test_draft_picking_validated_directly_is_gated_too(self):
        """Validate from draft with a blocking point: refused before anything
        is confirmed. A refused request is rolled back, so checks raised
        inside it would vanish with it while the message still named them
        and their numbers were burnt. The message names the transfer and the
        point and says to mark it as To Do; no check exists afterwards and no
        QC number is consumed."""
        self.Point.create({"name": "Visual", "product_id": self.steel.id})
        picking = self._picking(self.receipt_type, [(self.steel, 4)])
        self.assertEqual(picking.state, "draft")
        sequence = self.env["ir.sequence"].search([("code", "=", "drkds.quality.check")])
        next_before = sequence.number_next_actual
        with self.assertRaises(UserError) as cm, self.env.cr.savepoint():
            self._validate(picking)
        self.env.invalidate_all()
        message = str(cm.exception)
        self.assertIn(picking.name, message)
        self.assertIn("Visual", message)
        self.assertIn("Mark as To Do", message)
        self.assertNotIn("QC/", message)
        self.assertEqual(picking.state, "draft")
        self.assertFalse(self.Check.search([("picking_id", "=", picking.id)]))
        self.assertEqual(sequence.number_next_actual, next_before)

        picking.action_confirm()
        self.assertEqual(len(picking.drkds_quality_check_ids), 1)

    def test_draft_picking_with_only_an_advisory_point_validates_directly(self):
        self.Point.create({"name": "Advisory", "product_id": self.steel.id, "blocking": False})
        picking = self._picking(self.receipt_type, [(self.steel, 4)])
        self._validate(picking)
        self.assertEqual(picking.state, "done")
        self.assertEqual(picking.drkds_quality_check_ids.state, "todo")

    def test_gate_message_names_the_open_checks(self):
        self.Point.create({"name": "Visual", "product_id": self.steel.id})
        picking = self._picking(self.receipt_type, [(self.steel, 4)])
        picking.action_confirm()
        check = picking.drkds_quality_check_ids
        with self.assertRaises(UserError) as cm:
            self._validate(picking)
        self.assertIn(check.name, str(cm.exception))
        self.assertIn("Visual", str(cm.exception))

    # -- smart button ---------------------------------------------------
    def test_smart_button_action_is_scoped_to_the_picking(self):
        self.Point.create({"name": "Visual", "product_category_id": self.categ_raw.id})
        picking = self._picking(self.receipt_type, [(self.steel, 1), (self.copper, 1)])
        picking.action_confirm()
        action = picking.action_view_drkds_quality_checks()
        self.assertEqual(action["domain"], [("picking_id", "=", picking.id)])
        self.assertEqual(action["context"]["default_picking_id"], picking.id)
        found = self.Check.search(action["domain"])
        self.assertEqual(found, picking.drkds_quality_check_ids)

    def test_stock_user_can_decide_but_not_configure(self):
        user = self.env["res.users"].create({
            "name": "Inspector", "login": "qc.inspector",
            "group_ids": [(6, 0, self.env.ref("stock.group_stock_user").ids)],
        })
        self.Point.create({"name": "Visual", "product_id": self.steel.id})
        picking = self._picking(self.receipt_type, [(self.steel, 1)])
        picking.action_confirm()
        check = picking.drkds_quality_check_ids.with_user(user)
        check.action_pass()
        self.assertEqual(check.state, "pass")
        with self.assertRaises(AccessError):
            self.Point.with_user(user).create({"name": "Nope", "product_id": self.steel.id})

    # -- users of other apps --------------------------------------------
    def _transfer_user_without_inventory_rights(self):
        """A user granted transfers the way purchase_stock grants buyers and
        sale_stock grants salespeople: stock.picking and stock.move through
        their own app group, no Inventory group (same rights as
        purchase_stock's ir.model.access.csv gives purchase users)."""
        group = self.env["res.groups"].create({
            "name": "Buyer (test)",
            "implied_ids": [Command.link(self.env.ref("base.group_user").id)],
        })
        for model, write, unlink in (
            ("stock.picking", True, True),
            ("stock.move", True, False),
            ("stock.warehouse.orderpoint", False, False),
        ):
            self.env["ir.model.access"].create({
                "name": "test %s buyer" % model,
                "model_id": self.env["ir.model"]._get_id(model),
                "group_id": group.id,
                "perm_read": True, "perm_write": write,
                "perm_create": write, "perm_unlink": unlink,
            })
        user = self.env["res.users"].create({
            "name": "Buyer", "login": "qc.buyer", "group_ids": [Command.set(group.ids)],
        })
        self.assertFalse(user.has_group("stock.group_stock_user"))
        return user

    def test_user_without_inventory_rights_can_confirm_a_transfer(self):
        """A buyer confirming a purchase confirms its receipt. The checks are
        raised by the system whatever the confirming user may do with them
        (steel matches, tape does not: 1 check), and that user is not made a
        follower of checks they cannot open."""
        buyer = self._transfer_user_without_inventory_rights()
        self.Point.create({"name": "Visual", "product_category_id": self.categ_raw.id})
        picking = self._picking(self.receipt_type, [(self.steel, 2), (self.tape, 1)])
        picking.with_user(buyer).action_confirm()
        checks = self.Check.search([("picking_id", "=", picking.id)])
        self.assertEqual(len(checks), 1)
        self.assertEqual(checks.product_id, self.steel)
        self.assertNotIn(buyer.partner_id, checks.message_partner_ids)

    def test_user_without_inventory_rights_can_open_a_transfer(self):
        """The transfer form and search view a buyer or salesperson gets must
        not ask for quality fields they have no right to read; an Inventory
        user still gets the smart button and the filter."""
        buyer = self._transfer_user_without_inventory_rights()
        self.Point.create({"name": "Visual", "product_id": self.steel.id})
        picking = self._picking(self.receipt_type, [(self.steel, 2)])
        picking.action_confirm()
        ours = {"drkds_quality_check_ids", "drkds_quality_check_count", "drkds_quality_open_count"}

        views = self.env["stock.picking"].with_user(buyer).get_views(
            [(False, "form"), (False, "search")]
        )
        self.assertFalse(ours & set(views["models"]["stock.picking"]["fields"]))
        self.assertNotIn("action_view_drkds_quality_checks", views["views"]["form"]["arch"])
        self.assertNotIn("drkds_quality_open", views["views"]["search"]["arch"])
        self.env.invalidate_all()
        read = picking.with_user(buyer).web_read({"name": {}, "state": {}})
        self.assertEqual(read[0]["name"], picking.name)

        inspector = self.env["res.users"].create({
            "name": "Inspector", "login": "qc.inspector.views",
            "group_ids": [Command.set(self.env.ref("stock.group_stock_user").ids)],
        })
        views = self.env["stock.picking"].with_user(inspector).get_views(
            [(False, "form"), (False, "search")]
        )
        self.assertIn("action_view_drkds_quality_checks", views["views"]["form"]["arch"])
        self.assertIn("drkds_quality_open", views["views"]["search"]["arch"])
        self.env.invalidate_all()
        read = picking.with_user(inspector).web_read({"drkds_quality_open_count": {}})
        self.assertEqual(read[0]["drkds_quality_open_count"], 1)

    # -- multi-company --------------------------------------------------
    def test_points_and_checks_stay_in_their_company(self):
        """A point of company A raises nothing on a receipt of company B; a
        point of company B (same title, allowed per company) raises one check
        stamped company B, which a company-A-only user cannot see."""
        company_b = self.env["res.company"].create({"name": "QC Company B"})
        warehouse_b = self.env["stock.warehouse"].search([("company_id", "=", company_b.id)])
        self.assertEqual(len(warehouse_b), 1)
        self.Point.create({"name": "Visual", "product_category_id": self.categ_raw.id})

        def receipt_b():
            return self.env["stock.picking"].with_company(company_b).create({
                "picking_type_id": warehouse_b.in_type_id.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": warehouse_b.lot_stock_id.id,
                "move_ids": [Command.create({
                    "product_id": self.steel.id, "product_uom_qty": 3,
                    "location_id": self.supplier_location.id,
                    "location_dest_id": warehouse_b.lot_stock_id.id,
                })],
            })

        first = receipt_b()
        first.action_confirm()
        self.assertFalse(first.drkds_quality_check_ids)

        point_b = self.Point.with_company(company_b).create({
            "name": "Visual", "product_category_id": self.categ_raw.id,
            "company_id": company_b.id,
        })
        second = receipt_b()
        second.action_confirm()
        check_b = second.drkds_quality_check_ids
        self.assertEqual(len(check_b), 1)
        self.assertEqual(check_b.point_id, point_b)
        self.assertEqual(check_b.company_id, company_b)

        user_a = self.env["res.users"].create({
            "name": "Inspector A", "login": "qc.company.a",
            "company_id": self.company.id, "company_ids": [Command.set(self.company.ids)],
            "group_ids": [Command.set(self.env.ref("stock.group_stock_user").ids)],
        })
        self.assertFalse(self.Check.with_user(user_a).search([("id", "=", check_b.id)]))
        self.assertFalse(self.Point.with_user(user_a).search([("id", "=", point_b.id)]))
