from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMaterialRequest(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Request = cls.env["drkds.lite.material.request"]
        cls.company = cls.env.company
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.shelf = cls.env["stock.location"].create({
            "name": "Workshop",
            "usage": "internal",
            "location_id": cls.stock_location.id,
        })
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.bolt = cls.env["product.product"].create({
            "name": "Anchor Bolt",
            "is_storable": True,
            "type": "consu",
            "uom_id": cls.uom_unit.id,
        })
        cls.nut = cls.env["product.product"].create({
            "name": "Anchor Nut",
            "is_storable": True,
            "type": "consu",
            "uom_id": cls.uom_unit.id,
        })

        group_user = cls.env.ref("drkds_material_request_lite.group_material_request_user")
        group_approver = cls.env.ref(
            "drkds_material_request_lite.group_material_request_approver"
        )
        stock_user = cls.env.ref("stock.group_stock_user")
        cls.requester = cls.env["res.users"].create({
            "name": "Rita Requester",
            "login": "rita.requester",
            "group_ids": [(6, 0, (group_user | stock_user).ids)],
        })
        cls.approver = cls.env["res.users"].create({
            "name": "Alan Approver",
            "login": "alan.approver",
            "group_ids": [(6, 0, (group_approver | stock_user).ids)],
        })

    # -- helpers -------------------------------------------------------
    def _make_request(self, lines=None, user=None):
        user = user or self.requester
        lines = lines if lines is not None else [(self.bolt, 10.0)]
        return self.Request.with_user(user).create({
            "requester_id": user.id,
            "warehouse_id": self.warehouse.id,
            "location_dest_id": self.shelf.id,
            "reason": "Line 3 rebuild",
            "line_ids": [
                (0, 0, {"product_id": product.id, "product_qty": qty})
                for product, qty in lines
            ],
        })

    def _put_in_stock(self, product, qty, location=None):
        self.env["stock.quant"].with_context(inventory_mode=True).create({
            "product_id": product.id,
            "location_id": (location or self.stock_location).id,
            "inventory_quantity": qty,
        })._apply_inventory()

    def _validate(self, picking, quantities=None):
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = (
                quantities.get(move.product_id, move.product_uom_qty)
                if quantities else move.product_uom_qty
            )
            move.picked = True
        return picking.with_context(skip_backorder=True).button_validate()

    # -- numbering and defaults ---------------------------------------
    def test_request_takes_a_sequence_number(self):
        """A new request is numbered from the sequence, not left as New."""
        request = self._make_request()
        self.assertTrue(request.name.startswith("MR/"))
        self.assertNotEqual(request.name, "New")
        self.assertEqual(request.location_id, self.stock_location)
        self.assertEqual(request.state, "draft")

    # -- state machine -------------------------------------------------
    def test_cannot_approve_a_draft_request(self):
        """Approval is only defined out of Submitted."""
        request = self._make_request()
        with self.assertRaises(UserError):
            request.with_user(self.approver).action_approve()

    def test_cannot_submit_an_empty_request(self):
        request = self.Request.with_user(self.requester).create({
            "requester_id": self.requester.id,
            "warehouse_id": self.warehouse.id,
            "location_dest_id": self.shelf.id,
        })
        with self.assertRaises(UserError):
            request.action_submit()

    def test_cannot_submit_twice(self):
        request = self._make_request()
        request.action_submit()
        with self.assertRaises(UserError):
            request.action_submit()

    def test_cannot_refuse_an_approved_request(self):
        self._put_in_stock(self.bolt, 50)
        request = self._make_request()
        request.action_submit()
        request.with_user(self.approver).action_approve()
        with self.assertRaises(UserError):
            request.with_user(self.approver).action_refuse()

    def test_approved_request_lines_are_locked(self):
        """An approved request cannot have its content quietly changed."""
        self._put_in_stock(self.bolt, 50)
        request = self._make_request()
        request.action_submit()
        request.with_user(self.approver).action_approve()
        with self.assertRaises(UserError):
            request.write({"line_ids": [(0, 0, {
                "product_id": self.nut.id, "product_qty": 1.0,
            })]})

    def test_refused_request_can_be_resubmitted(self):
        request = self._make_request()
        request.action_submit()
        request.with_user(self.approver).action_refuse_with_reason("Too many")
        request.action_submit()
        self.assertEqual(request.state, "submitted")
        self.assertFalse(request.refusal_reason)

    # -- separation of duties -----------------------------------------
    def test_requester_cannot_approve_own_request(self):
        """Even with the approver group, you cannot sign off your own ask."""
        request = self._make_request(user=self.approver)
        request.action_submit()
        with self.assertRaises(UserError):
            request.with_user(self.approver).action_approve()

    def test_requester_sees_only_own_requests(self):
        mine = self._make_request()
        theirs = self._make_request(user=self.approver)
        visible = self.Request.with_user(self.requester).search([])
        self.assertIn(mine, visible)
        self.assertNotIn(theirs, visible)
        self.assertIn(theirs, self.Request.with_user(self.approver).search([]))

    # -- refusal -------------------------------------------------------
    def test_refusal_without_a_reason_is_refused(self):
        request = self._make_request()
        request.action_submit()
        with self.assertRaises(UserError):
            request.with_user(self.approver).action_refuse_with_reason("   ")
        self.assertEqual(request.state, "submitted")

    def test_refusal_with_a_reason_is_recorded(self):
        request = self._make_request()
        request.action_submit()
        wizard = self.env["drkds.lite.material.request.refuse"].with_user(self.approver).create({
            "request_id": request.id,
            "reason": "Budget exhausted for this quarter",
        })
        wizard.action_confirm()
        self.assertEqual(request.state, "refused")
        self.assertEqual(request.refusal_reason, "Budget exhausted for this quarter")
        self.assertEqual(request.approver_id, self.approver)

    # -- availability --------------------------------------------------
    def test_on_hand_reflects_real_stock_at_the_source_location(self):
        """The line reads the quant, and only at the request's own location."""
        request = self._make_request()
        line = request.line_ids
        self.assertEqual(line.qty_available, 0.0)
        self._put_in_stock(self.bolt, 40)
        line.invalidate_recordset(["qty_available"])
        self.assertEqual(line.qty_available, 40.0)
        # stock somewhere else must not show up here
        other = self.env["stock.location"].create({
            "name": "Far Shed", "usage": "internal",
            "location_id": self.warehouse.view_location_id.id,
        })
        self._put_in_stock(self.bolt, 15, location=other)
        line.invalidate_recordset(["qty_available"])
        self.assertEqual(line.qty_available, 40.0)

    # -- fulfilment ----------------------------------------------------
    def test_approval_creates_the_internal_transfer(self):
        self._put_in_stock(self.bolt, 50)
        self._put_in_stock(self.nut, 50)
        request = self._make_request(lines=[(self.bolt, 10.0), (self.nut, 4.0)])
        request.action_submit()
        request.with_user(self.approver).action_approve()

        self.assertEqual(request.state, "approved")
        self.assertEqual(request.picking_count, 1)
        picking = request.picking_ids
        self.assertEqual(picking.picking_type_id, self.warehouse.int_type_id)
        self.assertEqual(picking.location_id, self.stock_location)
        self.assertEqual(picking.location_dest_id, self.shelf)
        self.assertEqual(picking.origin, request.name)
        self.assertEqual(len(picking.move_ids), 2)
        self.assertEqual(
            sorted(picking.move_ids.mapped("product_uom_qty")), [4.0, 10.0]
        )
        self.assertEqual(
            picking.move_ids.mapped("drkds_request_line_id"), request.line_ids
        )

    def test_partial_fulfilment_leaves_the_request_open(self):
        self._put_in_stock(self.bolt, 50)
        request = self._make_request(lines=[(self.bolt, 10.0)])
        request.action_submit()
        request.with_user(self.approver).action_approve()
        self._validate(request.picking_ids, {self.bolt: 6.0})

        self.assertEqual(request.line_ids.qty_fulfilled, 6.0)
        self.assertEqual(request.line_ids.qty_outstanding, 4.0)
        self.assertEqual(request.outstanding_qty, 4.0)
        self.assertFalse(request.is_fully_fulfilled)
        self.assertEqual(request.state, "approved")

    def test_full_fulfilment_closes_the_request(self):
        self._put_in_stock(self.bolt, 50)
        request = self._make_request(lines=[(self.bolt, 10.0)])
        request.action_submit()
        request.with_user(self.approver).action_approve()
        self._validate(request.picking_ids)

        self.assertEqual(request.line_ids.qty_fulfilled, 10.0)
        self.assertEqual(request.outstanding_qty, 0.0)
        self.assertTrue(request.is_fully_fulfilled)
        self.assertEqual(request.state, "done")

    def test_remainder_can_be_transferred_and_closes_the_request(self):
        """A second transfer covers the shortfall and finishes the request."""
        self._put_in_stock(self.bolt, 50)
        request = self._make_request(lines=[(self.bolt, 10.0)])
        request.action_submit()
        request.with_user(self.approver).action_approve()
        self._validate(request.picking_ids, {self.bolt: 6.0})

        request.action_create_transfer()
        self.assertEqual(request.picking_count, 2)
        remainder = request.picking_ids.filtered(lambda p: p.state != "done")
        self.assertEqual(remainder.move_ids.product_uom_qty, 4.0)
        self._validate(remainder)
        self.assertEqual(request.state, "done")
        with self.assertRaises(UserError):
            request.action_create_transfer()

    def test_cancel_cancels_the_open_transfer(self):
        self._put_in_stock(self.bolt, 50)
        request = self._make_request(lines=[(self.bolt, 10.0)])
        request.action_submit()
        request.with_user(self.approver).action_approve()
        request.action_cancel()
        self.assertEqual(request.state, "cancel")
        self.assertEqual(request.picking_ids.state, "cancel")
