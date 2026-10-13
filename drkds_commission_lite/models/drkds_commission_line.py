from odoo import api, fields, models
from odoo.exceptions import UserError


class DrkdsCommissionLine(models.Model):
    """One commission entry, written per invoice line when the invoice posts."""
    _name = "drkds.commission.line"
    _description = "Commission Line"
    _order = "date desc, id desc"
    _check_company_auto = True

    move_id = fields.Many2one(
        "account.move", string="Invoice", required=True, index=True, ondelete="cascade",
        readonly=True,
    )
    move_line_id = fields.Many2one(
        "account.move.line", string="Invoice Line", index=True, ondelete="cascade",
        readonly=True,
    )
    move_type = fields.Selection(related="move_id.move_type", store=True)
    user_id = fields.Many2one(
        "res.users", string="Salesperson", required=True, index=True, readonly=True,
        ondelete="restrict",
    )
    partner_id = fields.Many2one(
        "res.partner", string="Customer", readonly=True, ondelete="restrict",
    )
    date = fields.Date(string="Invoice Date", required=True, index=True, readonly=True)
    product_id = fields.Many2one(
        "product.product", string="Product", readonly=True, ondelete="set null",
    )
    categ_id = fields.Many2one(
        "product.category", string="Product Category", readonly=True, ondelete="set null",
    )
    base_amount = fields.Monetary(
        string="Base", currency_field="currency_id", readonly=True,
        help="Untaxed amount of the invoice line in company currency; negative on a credit note.",
    )
    rate = fields.Float(string="Rate (%)", digits=(5, 2), readonly=True)
    amount = fields.Monetary(
        string="Commission", currency_field="currency_id", readonly=True,
    )
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True)
    company_id = fields.Many2one(
        "res.company", string="Company", required=True, index=True, readonly=True,
    )
    state = fields.Selection(
        [("unpaid", "Unpaid"), ("paid", "Paid")], string="Status",
        default="unpaid", required=True, index=True, copy=False,
    )
    paid_date = fields.Date(string="Paid On", copy=False)

    # -- computation ------------------------------------------------------
    @api.model
    def _prepare_values(self, line):
        """Values for the commission line of invoice line ``line``, or None."""
        move = line.move_id
        user = move.invoice_user_id
        if not user:
            return None
        product = line.product_id
        categ = product.categ_id
        rate = self.env["drkds.commission.rate"]._get_rate(user, categ, move.company_id)
        if not rate:
            return None
        company_currency = move.company_id.currency_id
        base = line.price_subtotal
        if move.currency_id != company_currency:
            base = move.currency_id._convert(
                base, company_currency, move.company_id,
                move.invoice_date or fields.Date.context_today(move),
            )
        sign = -1 if move.move_type == "out_refund" else 1
        base = company_currency.round(sign * base)
        return {
            "move_id": move.id,
            "move_line_id": line.id,
            "user_id": user.id,
            "partner_id": move.commercial_partner_id.id,
            "date": move.invoice_date or fields.Date.context_today(move),
            "product_id": product.id,
            "categ_id": categ.id,
            "base_amount": base,
            "rate": rate,
            "amount": company_currency.round(base * rate / 100.0),
            "currency_id": company_currency.id,
            "company_id": move.company_id.id,
        }

    @api.model
    def _generate_for_moves(self, moves):
        """(Re)compute the commission lines of ``moves``, which must be posted.

        Existing unpaid lines are dropped first, so posting twice never
        duplicates. A move carrying paid lines is left alone: that commission
        has already been settled.
        """
        Line = self.sudo()
        moves = moves.filtered(
            lambda m: m.state == "posted" and m.move_type in ("out_invoice", "out_refund")
        )
        if not moves:
            return Line
        existing = Line.search([("move_id", "in", moves.ids)])
        locked = existing.filtered(lambda l: l.state == "paid").mapped("move_id")
        (existing - existing.filtered(lambda l: l.move_id in locked)).unlink()
        vals_list = []
        for move in moves - locked:
            for line in move.invoice_line_ids.filtered(lambda l: l.display_type == "product"):
                vals = self._prepare_values(line)
                if vals:
                    vals_list.append(vals)
        return Line.create(vals_list)

    # -- paid / unpaid ------------------------------------------------------
    def _check_can_settle(self):
        if not (self.env.user.has_group("sales_team.group_sale_manager")
                or self.env.user.has_group("account.group_account_manager")):
            raise UserError(self.env._(
                "Only a sales or accounting manager can mark commission lines as paid or unpaid."
            ))

    def action_mark_paid(self):
        self._check_can_settle()
        self.filtered(lambda l: l.state == "unpaid").write({
            "state": "paid",
            "paid_date": fields.Date.context_today(self),
        })
        return True

    def action_mark_unpaid(self):
        self._check_can_settle()
        self.filtered(lambda l: l.state == "paid").write({"state": "unpaid", "paid_date": False})
        return True

    @api.ondelete(at_uninstall=False)
    def _unlink_except_paid(self):
        if any(l.state == "paid" for l in self):
            raise UserError(self.env._(
                "A paid commission line cannot be deleted. Mark it unpaid first."
            ))
