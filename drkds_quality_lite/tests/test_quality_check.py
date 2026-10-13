import re

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
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.Point.create({"name": "Visual", "product_id": self.copper.id})

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
        """Validate from draft: super confirms the moves, the checks are
        raised, and the gate in _action_done still stops it. The refusal
        rolls the whole request back (checks included), so the proof that
        the checks existed is the message naming the point."""
        self.Point.create({"name": "Visual", "product_id": self.steel.id})
        picking = self._picking(self.receipt_type, [(self.steel, 4)])
        self.assertEqual(picking.state, "draft")
        with self.assertRaises(UserError) as cm:
            self._validate(picking)
        self.assertIn("Visual", str(cm.exception))
        self.assertNotEqual(picking.state, "done")

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
