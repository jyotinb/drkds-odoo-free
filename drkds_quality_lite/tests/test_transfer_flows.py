"""Checks follow their moves through backorders, splits and cancellations.

Every case uses one blocking point on the QC Raw Materials category, which
matches Steel Sheet 2mm (sub-category) and Copper Wire, so a receipt of
steel 10 + copper 5 raises exactly two checks on confirmation.
"""
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import QualityCase


@tagged("post_install", "-at_install")
class TestTransferFlows(QualityCase):

    def setUp(self):
        super().setUp()
        self.point = self.Point.create({
            "name": "Visual", "product_category_id": self.categ_raw.id,
        })
        self.receipt = self._picking(self.receipt_type, [(self.steel, 10), (self.copper, 5)])
        self.receipt.action_confirm()
        self.assertEqual(len(self.receipt.drkds_quality_check_ids), 2)

    def _check(self, picking, product):
        return picking.drkds_quality_check_ids.filtered(lambda c: c.product_id == product)

    def _backorder(self, picking):
        return self.env["stock.picking"].search([("backorder_id", "=", picking.id)])

    def test_backorder_carries_the_check_of_the_remaining_quantity(self):
        """6 of 10 steel and all 5 copper arrive, both checks passed.
        Original: done, 2 checks passed, 0 open. Backorder: steel 4 with one
        new check to do, and it cannot be validated until that check passes."""
        self.receipt.drkds_quality_check_ids.action_pass()
        self._move(self.receipt, self.steel).quantity = 6
        self.receipt.move_ids.picked = True
        self._validate_as_is(self.receipt, backorder=True)

        self.assertEqual(self.receipt.state, "done")
        self.assertEqual(len(self.receipt.drkds_quality_check_ids), 2)
        self.assertEqual(set(self.receipt.drkds_quality_check_ids.mapped("state")), {"pass"})
        self.assertEqual(self.receipt.drkds_quality_open_count, 0)

        backorder = self._backorder(self.receipt)
        self.assertEqual(len(backorder), 1)
        self.assertEqual(backorder.move_ids.product_id, self.steel)
        self.assertEqual(backorder.move_ids.product_uom_qty, 4)
        check = backorder.drkds_quality_check_ids
        self.assertEqual(len(check), 1)
        self.assertEqual(check.move_id, backorder.move_ids)
        self.assertEqual(check.state, "todo")
        self.assertEqual(check.picking_type_id, self.receipt_type)
        self.assertEqual(backorder.drkds_quality_open_count, 1)

        backorder.move_ids.picked = True
        with self.assertRaises(UserError):
            self._validate_as_is(backorder)
        self.assertNotEqual(backorder.state, "done")
        check.action_pass()
        self._validate_as_is(backorder)
        self.assertEqual(backorder.state, "done")

    def test_goods_not_delivered_go_to_the_backorder_with_their_check(self):
        """All 10 steel arrive and pass; no copper arrives. The copper check
        is still to do, but it concerns goods that are not here: the receipt
        validates and the copper move goes to the backorder with its check."""
        steel_check = self._check(self.receipt, self.steel)
        copper_check = self._check(self.receipt, self.copper)
        steel_check.action_pass()
        self._move(self.receipt, self.copper).quantity = 0
        self._move(self.receipt, self.steel).picked = True
        self._validate_as_is(self.receipt, backorder=True)

        self.assertEqual(self.receipt.state, "done")
        self.assertEqual(self.receipt.drkds_quality_check_ids, steel_check)
        backorder = self._backorder(self.receipt)
        self.assertEqual(backorder.move_ids.product_id, self.copper)
        self.assertEqual(backorder.drkds_quality_check_ids, copper_check)
        self.assertEqual(copper_check.state, "todo")

    def test_goods_not_delivered_without_backorder_drop_their_open_check(self):
        """Same receipt, closed without a backorder: the copper move is
        cancelled and its open check removed; steel is done."""
        steel_check = self._check(self.receipt, self.steel)
        copper_check = self._check(self.receipt, self.copper)
        steel_check.action_pass()
        self._move(self.receipt, self.copper).quantity = 0
        self._move(self.receipt, self.steel).picked = True
        self._validate_as_is(self.receipt, backorder=False)

        self.assertEqual(self.receipt.state, "done")
        self.assertEqual(self._move(self.receipt, self.copper).state, "cancel")
        self.assertFalse(copper_check.exists())
        self.assertEqual(self.receipt.drkds_quality_check_ids, steel_check)

    def test_failed_check_of_a_cancelled_move_does_not_hold_up_the_rest(self):
        """Copper fails and its move is cancelled (the goods are refused).
        The failed check stays as history but no longer blocks the steel."""
        self._check(self.receipt, self.steel).action_pass()
        copper_check = self._check(self.receipt, self.copper)
        copper_check.action_fail()
        self._move(self.receipt, self.copper)._action_cancel()
        self._move(self.receipt, self.steel).picked = True
        self._validate_as_is(self.receipt)

        self.assertEqual(self.receipt.state, "done")
        self.assertEqual(copper_check.state, "fail")
        self.assertEqual(copper_check.picking_id, self.receipt)

    def test_refused_goods_closed_without_backorder(self):
        """The manual's flow for refused goods: copper fails, its quantity is
        set to 0 and the receipt is validated without a backorder. Copper is
        cancelled, its failed check stays as the record, steel is received."""
        self._check(self.receipt, self.steel).action_pass()
        copper_check = self._check(self.receipt, self.copper)
        copper_check.action_fail()
        self._move(self.receipt, self.copper).quantity = 0
        self._move(self.receipt, self.steel).picked = True
        self._validate_as_is(self.receipt, backorder=False)

        self.assertEqual(self.receipt.state, "done")
        self.assertEqual(self._move(self.receipt, self.copper).state, "cancel")
        self.assertEqual(copper_check.state, "fail")
        self.assertEqual(copper_check.picking_id, self.receipt)
        self.assertFalse(self._backorder(self.receipt))
        on_hand = self.steel.with_context(location=self.stock_location.id).qty_available
        self.assertEqual(on_hand, 10)

    def test_failed_check_on_goods_being_received_still_blocks(self):
        """The gate narrows to the goods being validated, it does not open:
        a failed check on a move with a quantity still refuses validation,
        with or without backorder."""
        self._check(self.receipt, self.steel).action_pass()
        self._check(self.receipt, self.copper).action_fail()
        self._move(self.receipt, self.copper).quantity = 1
        self.receipt.move_ids.picked = True
        for backorder in (True, False):
            with self.assertRaises(UserError):
                self._validate_as_is(self.receipt, backorder=backorder)
        self.assertNotEqual(self.receipt.state, "done")

    def test_split_transfer_moves_the_checks_with_the_moves(self):
        """Split with steel 4 of 10 and copper 0: the original keeps steel 4
        and its check; the split-off transfer gets steel 6 with a new check
        and copper 5 with its existing check."""
        steel_check = self._check(self.receipt, self.steel)
        copper_check = self._check(self.receipt, self.copper)
        self._move(self.receipt, self.steel).quantity = 4
        self._move(self.receipt, self.copper).quantity = 0
        self.receipt.action_split_transfer()

        split = self._backorder(self.receipt)
        self.assertEqual(self.receipt.move_ids.product_id, self.steel)
        self.assertEqual(self.receipt.move_ids.product_uom_qty, 4)
        self.assertEqual(self.receipt.drkds_quality_check_ids, steel_check)
        self.assertEqual(len(split.drkds_quality_check_ids), 2)
        self.assertIn(copper_check, split.drkds_quality_check_ids)
        new_steel = self._check(split, self.steel)
        self.assertEqual(new_steel.move_id, self._move(split, self.steel))
        self.assertEqual(new_steel.move_id.product_uom_qty, 6)
        self.assertEqual(new_steel.state, "todo")
