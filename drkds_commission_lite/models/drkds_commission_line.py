from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import UserError

# A paid line and the unpaid lines that adjust it share these values.
_KEY_FIELDS = (
    "move_line_id", "user_id", "partner_id", "date", "product_id", "categ_id",
    "rate", "currency_id", "company_id",
)


def _line_key(vals):
    return tuple(vals[name] for name in _KEY_FIELDS)


class DrkdsCommissionLine(models.Model):
    """One commission entry, written per invoice line when the invoice posts.

    Also the difference from a paid line when its invoice changes afterwards
    (see ``_generate_for_moves``).
    """
    _name = "drkds.commission.line"
    _description = "Commission Line"
    _order = "date desc, id desc"
    _check_company_auto = True

    move_id = fields.Many2one(
        "account.move", string="Invoice", required=True, index=True, ondelete="cascade",
        readonly=True,
    )
    move_line_id = fields.Many2one(
        "account.move.line", string="Invoice Line", index=True, ondelete="set null",
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
        help="Untaxed amount of the invoice line in company currency, as booked; negative on a credit note.",
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
    def _prepare_values(self, line, earned=None):
        """Values for the commission line of invoice line ``line``, or None.

        ``earned`` is given for a document that reverses another one (a credit
        note made from an invoice): ``{product_id: (user_id, rate)}`` of what that
        invoice earned. The reversal takes back at that rate, from that
        salesperson, and only for products the invoice earned commission on.
        """
        move = line.move_id
        product = line.product_id
        if earned is not None:
            if product.id not in earned:
                return None
            user_id, rate = earned[product.id]
            user = self.env["res.users"].browse(user_id)
        else:
            user = move.invoice_user_id
            if not user:
                return None
            rate = self.env["drkds.commission.rate"]._get_rate(user, product.categ_id, move.company_id)
        if not rate:
            return None
        company_currency = move.company_id.currency_id
        # The amount as booked, in company currency at the document's own rate
        # (which may be typed in, and which a credit note copies from its invoice).
        # Revenue is a credit, so this is positive on an invoice, negative on a refund.
        base = company_currency.round(-line.balance)
        return {
            "move_id": move.id,
            "move_line_id": line.id,
            "user_id": user.id,
            "partner_id": move.commercial_partner_id.id,
            "date": move.invoice_date or move.date,
            "product_id": product.id,
            "categ_id": product.categ_id.id,
            "base_amount": base,
            "rate": rate,
            "amount": company_currency.round(base * rate / 100.0),
            "currency_id": company_currency.id,
            "company_id": move.company_id.id,
        }

    @api.model
    def _earned_by_product(self, move):
        """``{product_id: (user_id, rate)}`` of the commission ``move`` carries now.

        Lines that offset each other (a paid line and its take-back) cancel out,
        so only what the document currently earns remains.
        """
        currency = move.company_id.currency_id
        net = defaultdict(float)
        for line in self.sudo().search([("move_id", "=", move.id)]):
            net[line.product_id.id, line.user_id.id, line.rate] += line.base_amount
        earned = {}
        for (product_id, user_id, rate), base in sorted(net.items(), key=lambda item: abs(item[1])):
            if not currency.is_zero(base):
                earned[product_id] = (user_id, rate)  # the largest base wins
        return earned

    @api.model
    def _generate_for_moves(self, moves):
        """Bring the commission lines of ``moves`` in line with their current state.

        Called on posting, on reset to draft (which cancel goes through) and when
        the salesperson of a posted invoice changes. Unpaid lines are rewritten.
        Paid lines are a record of money paid out and are never touched: when the
        commission a document earns now (nothing in draft or cancelled) differs
        from what was paid, the difference is written as new unpaid lines,
        negative where commission is taken back. Calling it twice changes nothing.
        """
        Line = self.sudo()
        moves = moves.filtered(lambda m: m.move_type in ("out_invoice", "out_refund"))
        if not moves:
            return Line
        existing = Line.search([("move_id", "in", moves.ids)])
        paid = existing.filtered(lambda l: l.state == "paid")
        (existing - paid).unlink()
        paid_by_move = defaultdict(lambda: Line)
        for line in paid:
            paid_by_move[line.move_id] |= line

        vals_list = []
        for move in moves:
            # key -> [values, base, amount]; target first, then minus what was paid.
            delta = {}
            if move.state == "posted":
                origin = move.reversed_entry_id
                earned = (
                    self._earned_by_product(origin)
                    if origin.move_type in ("out_invoice", "out_refund") else None
                )
                for inv_line in move.invoice_line_ids.filtered(lambda l: l.display_type == "product"):
                    vals = self._prepare_values(inv_line, earned)
                    if vals:
                        delta[_line_key(vals)] = [vals, vals["base_amount"], vals["amount"]]
            for line in paid_by_move[move]:
                vals = {name: line[name] for name in _KEY_FIELDS}
                vals = {k: v.id if isinstance(v, models.BaseModel) else v for k, v in vals.items()}
                entry = delta.setdefault(_line_key(vals), [vals, 0.0, 0.0])
                entry[1] -= line.base_amount
                entry[2] -= line.amount
            for vals, base, amount in delta.values():
                currency = self.env["res.currency"].browse(vals["currency_id"])
                base, amount = currency.round(base), currency.round(amount)
                if currency.is_zero(base) and currency.is_zero(amount):
                    continue
                vals_list.append(dict(vals, move_id=move.id, base_amount=base, amount=amount))
        return Line.create(vals_list)

    # -- paid / unpaid ------------------------------------------------------
    def _check_can_settle(self):
        if not (self.env.user.has_group("sales_team.group_sale_manager")
                or self.env.user.has_group("account.group_account_manager")):
            raise UserError(self.env._(
                "Only a sales or accounting manager can mark commission lines as paid or unpaid."
            ))
        # Lines are read-only for everyone: the buttons are the only way to settle
        # them, so check what the manager may see, then write as the system.
        self.check_access("read")

    def action_mark_paid(self):
        self._check_can_settle()
        self.sudo().filtered(lambda l: l.state == "unpaid").write({
            "state": "paid",
            "paid_date": fields.Date.context_today(self),
        })
        return True

    def action_mark_unpaid(self):
        self._check_can_settle()
        self.sudo().filtered(lambda l: l.state == "paid").write({"state": "unpaid", "paid_date": False})
        return True

    @api.ondelete(at_uninstall=False)
    def _unlink_except_paid(self):
        if any(l.state == "paid" for l in self):
            raise UserError(self.env._(
                "A paid commission line cannot be deleted. Mark it unpaid first."
            ))
