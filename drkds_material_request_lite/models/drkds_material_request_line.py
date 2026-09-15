from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DrkdsMaterialRequestLine(models.Model):
    """One product asked for on a material request.

    The line keeps three quantities apart: what was asked for, what has
    actually been delivered by a done transfer, and the difference. The
    delivered figure is read back from the stock moves the line created, never
    typed in, so the request and the warehouse can never disagree.
    """

    _name = "drkds.material.request.line"
    _description = "Material Request Line"
    _order = "request_id, sequence, id"

    sequence = fields.Integer(default=10)
    request_id = fields.Many2one(
        "drkds.material.request", string="Request", required=True,
        ondelete="cascade", index=True,
    )
    company_id = fields.Many2one(
        related="request_id.company_id", store=True, index=True,
    )
    state = fields.Selection(related="request_id.state", store=True, string="Status")
    product_id = fields.Many2one(
        "product.product", string="Product", required=True,
        domain="[('is_storable', '=', True)]",
        help="Only storable products can be issued from stock.",
    )
    name = fields.Char(
        string="Description", compute="_compute_name", store=True, readonly=False,
        precompute=True,
    )
    product_qty = fields.Float(
        string="Quantity", required=True, default=1.0, digits="Product Unit",
    )
    product_uom_id = fields.Many2one(
        "uom.uom", string="Unit", compute="_compute_product_uom_id",
        store=True, readonly=False, required=True, precompute=True,
    )
    move_ids = fields.One2many(
        "stock.move", "drkds_request_line_id", string="Stock Moves", copy=False,
    )
    qty_fulfilled = fields.Float(
        string="Fulfilled", compute="_compute_qty_fulfilled", store=True,
        digits="Product Unit",
        help="Quantity actually delivered by completed transfers.",
    )
    qty_outstanding = fields.Float(
        string="Outstanding", compute="_compute_qty_fulfilled", store=True,
        digits="Product Unit",
    )
    qty_available = fields.Float(
        string="On Hand", compute="_compute_qty_available", digits="Product Unit",
        help="Quantity of this product on hand at the request's source "
        "location, in the line's unit of measure.",
    )

    _qty_positive = models.Constraint(
        "CHECK(product_qty > 0)",
        "A requested quantity must be greater than zero.",
    )

    @api.depends("product_id")
    def _compute_name(self):
        for line in self:
            if line.product_id and not line.name:
                line.name = line.product_id.display_name
            elif not line.product_id:
                line.name = line.name or False

    @api.depends("product_id")
    def _compute_product_uom_id(self):
        for line in self:
            line.product_uom_id = line.product_id.uom_id

    @api.depends(
        "move_ids.state", "move_ids.quantity", "move_ids.product_uom",
        "product_qty",
    )
    def _compute_qty_fulfilled(self):
        for line in self:
            done = 0.0
            for move in line.move_ids.filtered(lambda m: m.state == "done"):
                done += move.product_uom._compute_quantity(
                    move.quantity, line.product_uom_id or move.product_uom
                ) if move.product_uom else move.quantity
            line.qty_fulfilled = done
            line.qty_outstanding = max(line.product_qty - done, 0.0)

    @api.depends("product_id", "product_uom_id", "request_id.location_id")
    def _compute_qty_available(self):
        for line in self:
            location = line.request_id.location_id
            if not line.product_id or not location:
                line.qty_available = 0.0
                continue
            qty = line.product_id.with_context(
                location=location.id, company_owned=True
            ).qty_available
            uom = line.product_uom_id or line.product_id.uom_id
            line.qty_available = line.product_id.uom_id._compute_quantity(qty, uom)

    @api.constrains("product_id", "product_uom_id")
    def _check_uom(self):
        for line in self:
            if not line.product_id or not line.product_uom_id:
                continue
            if not line.product_uom_id._has_common_reference(line.product_id.uom_id):
                raise ValidationError(
                    _("Unit %(uom)s cannot measure %(product)s.",
                      uom=line.product_uom_id.display_name,
                      product=line.product_id.display_name)
                )

    def _prepare_stock_move_vals(self):
        """Values for the internal move that fulfils what is left of this line."""
        self.ensure_one()
        request = self.request_id
        return {
            # stock.move has no "name" in Odoo 19; the line label is
            # description_picking.
            "description_picking": self.name or self.product_id.display_name,
            "product_id": self.product_id.id,
            "product_uom_qty": self.qty_outstanding,
            "product_uom": self.product_uom_id.id,
            "location_id": request.location_id.id,
            "location_dest_id": request.location_dest_id.id,
            "company_id": request.company_id.id,
            "drkds_request_line_id": self.id,
        }
