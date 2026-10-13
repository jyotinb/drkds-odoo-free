from odoo.tests import TransactionCase


class QualityCase(TransactionCase):
    """Shared fixtures: one warehouse, three products in two categories."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Point = cls.env["drkds.quality.point"]
        cls.Check = cls.env["drkds.quality.check"]
        cls.company = cls.env.company
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.company.id)], limit=1
        )
        cls.receipt_type = cls.warehouse.in_type_id
        cls.delivery_type = cls.warehouse.out_type_id
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.supplier_location = cls.env.ref("stock.stock_location_suppliers")
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")

        cls.categ_raw = cls.env["product.category"].create({"name": "QC Raw Materials"})
        cls.categ_raw_sub = cls.env["product.category"].create({
            "name": "QC Metals", "parent_id": cls.categ_raw.id,
        })
        cls.categ_consu = cls.env["product.category"].create({"name": "QC Consumables"})
        cls.steel = cls.env["product.product"].create({
            "name": "Steel Sheet 2mm", "type": "consu", "is_storable": True,
            "categ_id": cls.categ_raw_sub.id, "uom_id": cls.uom_unit.id,
        })
        cls.copper = cls.env["product.product"].create({
            "name": "Copper Wire", "type": "consu", "is_storable": True,
            "categ_id": cls.categ_raw.id, "uom_id": cls.uom_unit.id,
        })
        cls.tape = cls.env["product.product"].create({
            "name": "Packing Tape", "type": "consu", "is_storable": True,
            "categ_id": cls.categ_consu.id, "uom_id": cls.uom_unit.id,
        })
        cls.partner = cls.env["res.partner"].create({"name": "Bharat Metals"})

    def _picking(self, picking_type, lines, partner=None):
        """A transfer of ``picking_type`` with one move per (product, qty)."""
        if picking_type.code == "incoming":
            src, dest = self.supplier_location, self.stock_location
        else:
            src, dest = self.stock_location, self.customer_location
        return self.env["stock.picking"].create({
            "picking_type_id": picking_type.id,
            "partner_id": (partner or self.partner).id,
            "location_id": src.id,
            "location_dest_id": dest.id,
            "move_ids": [
                (0, 0, {
                    "product_id": product.id,
                    "product_uom_qty": qty,
                    "product_uom": product.uom_id.id,
                    "location_id": src.id,
                    "location_dest_id": dest.id,
                })
                for product, qty in lines
            ],
        })

    def _validate(self, picking):
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
            move.picked = True
        return picking.with_context(
            skip_backorder=True, picking_ids_not_to_backorder=picking.ids
        ).button_validate()

    def _validate_as_is(self, picking, backorder=True):
        """Validate with the quantities and picked flags already set, the
        way the backorder dialog's two buttons do."""
        return picking.with_context(
            skip_backorder=True,
            picking_ids_not_to_backorder=[] if backorder else picking.ids,
        ).button_validate()

    def _move(self, picking, product):
        return picking.move_ids.filtered(lambda m: m.product_id == product)

    def _put_in_stock(self, product, qty):
        self.env["stock.quant"].with_context(inventory_mode=True).create({
            "product_id": product.id,
            "location_id": self.stock_location.id,
            "inventory_quantity": qty,
        })._apply_inventory()
