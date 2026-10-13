"""End-to-end: a receipt of three products against two control points.

Hand-computed expectations
--------------------------
Points
  P1 "Visual inspection"  category QC Raw Materials, receipts only, pass/fail, blocking
  P2 "Sheet thickness"    product Steel Sheet 2mm, measure 1.8..2.2 mm, blocking
Receipt
  Steel Sheet 2mm  x 50   category QC Metals (child of QC Raw Materials) -> P1 + P2 = 2 checks
  Copper Wire      x 20   category QC Raw Materials                      -> P1      = 1 check
  Packing Tape     x 100  category QC Consumables                        -> none    = 0 checks
                                                                   total      3 checks
Flow
  confirm        -> 3 checks to do, open 3/3, validate refused
  pass both P1   -> open 1/3, validate still refused (P2 to do)
  measure 2.5 mm -> P2 fails, open 1/3, validate refused
  reset, 2.05 mm -> P2 passes, open 0/3, validate accepted, receipt done
  stock on hand afterwards: steel 50, copper 20, tape 100
Delivery afterwards of 5 steel: P1 is receipts-only, so exactly 1 check (P2).
"""
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import QualityCase


@tagged("post_install", "-at_install")
class TestScenarioReceipt(QualityCase):

    def test_receipt_of_three_products_with_two_points(self):
        p1 = self.Point.create({
            "name": "Visual inspection",
            "product_category_id": self.categ_raw.id,
            "picking_type_ids": [(6, 0, self.receipt_type.ids)],
            "instructions": "<p>Look for dents, rust and torn packaging.</p>",
        })
        p2 = self.Point.create({
            "name": "Sheet thickness",
            "product_id": self.steel.id,
            "check_type": "measure", "norm_min": 1.8, "norm_max": 2.2,
            "measure_unit": "mm",
        })

        receipt = self._picking(self.receipt_type, [
            (self.steel, 50), (self.copper, 20), (self.tape, 100),
        ])
        receipt.action_confirm()

        checks = receipt.drkds_quality_check_ids
        self.assertEqual(len(checks), 3)
        steel_checks = checks.filtered(lambda c: c.product_id == self.steel)
        copper_checks = checks.filtered(lambda c: c.product_id == self.copper)
        tape_checks = checks.filtered(lambda c: c.product_id == self.tape)
        self.assertEqual(len(steel_checks), 2)
        self.assertEqual(steel_checks.mapped("point_id"), p1 | p2)
        self.assertEqual(copper_checks.point_id, p1)
        self.assertFalse(tape_checks)
        self.assertEqual(receipt.drkds_quality_check_count, 3)
        self.assertEqual(receipt.drkds_quality_open_count, 3)
        # the inspector sees the point's instructions on the check
        self.assertIn("dents", copper_checks.instructions)

        with self.assertRaises(UserError):
            self._validate(receipt)
        self.assertNotEqual(receipt.state, "done")

        visual = checks.filtered(lambda c: c.point_id == p1)
        visual.action_pass()
        self.assertEqual(receipt.drkds_quality_open_count, 1)
        with self.assertRaises(UserError):
            self._validate(receipt)

        thickness = checks.filtered(lambda c: c.point_id == p2)
        thickness.measure = 2.5
        thickness.action_measure()
        self.assertEqual(thickness.state, "fail")
        self.assertEqual(receipt.drkds_quality_open_count, 1)
        with self.assertRaises(UserError):
            self._validate(receipt)

        thickness.action_reset_todo()
        thickness.measure = 2.05
        thickness.action_measure()
        self.assertEqual(thickness.state, "pass")
        self.assertEqual(receipt.drkds_quality_open_count, 0)

        self._validate(receipt)
        self.assertEqual(receipt.state, "done")
        self.assertEqual(set(checks.mapped("state")), {"pass"})
        self.assertEqual(set(checks.mapped("user_id.id")), {self.env.user.id})

        for product, qty in [(self.steel, 50), (self.copper, 20), (self.tape, 100)]:
            on_hand = product.with_context(location=self.stock_location.id).qty_available
            self.assertEqual(on_hand, qty, product.name)

        delivery = self._picking(self.delivery_type, [(self.steel, 5)])
        delivery.action_confirm()
        self.assertEqual(len(delivery.drkds_quality_check_ids), 1)
        self.assertEqual(delivery.drkds_quality_check_ids.point_id, p2)
