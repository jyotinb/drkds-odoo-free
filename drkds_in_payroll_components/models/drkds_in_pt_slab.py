from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

MONTH_SELECTION = [
    ("1", "January"), ("2", "February"), ("3", "March"), ("4", "April"),
    ("5", "May"), ("6", "June"), ("7", "July"), ("8", "August"),
    ("9", "September"), ("10", "October"), ("11", "November"), ("12", "December"),
]


class DrkdsInPtSlab(models.Model):
    """One monthly professional tax slab for one state.

    Professional tax is a **state** levy, so there is no national rate: every
    state publishes its own slab table, its own exemptions and its own
    collection frequency. This model holds a wage band per state with the
    monthly tax due, plus the special-month rule used by states such as
    Maharashtra and Karnataka, which collect a higher amount in one month of
    the year so that the annual total reaches the INR 2,500 cap.

    The module ships slabs for a handful of major states only, as a starting
    point. They are ordinary data records: the user must verify them against
    the current state notification and add the states they operate in.
    """

    _name = "drkds.in.pt.slab"
    _description = "India Professional Tax Slab"
    _order = "state_id, effective_from desc, amount_from"

    state_id = fields.Many2one(
        "res.country.state", string="State", required=True,
        domain="[('country_id.code', '=', 'IN')]",
        help="The state whose professional tax schedule this slab belongs to.",
    )
    effective_from = fields.Date(
        required=True,
        help="First day from which this slab table applies for the state.",
    )
    amount_from = fields.Float(
        string="Monthly Wage From", default=0.0,
        help="Lower bound of the band, inclusive.",
    )
    amount_to = fields.Float(
        string="Monthly Wage To", default=0.0,
        help="Upper bound of the band, inclusive. Leave at zero for the "
        "open-ended top band.",
    )
    monthly_tax = fields.Float(
        string="Monthly Tax", default=0.0,
        help="Professional tax deducted in an ordinary month.",
    )
    special_month = fields.Selection(
        MONTH_SELECTION, string="Special Month",
        help="Month in which a different amount is collected, for example "
        "February in Maharashtra and Karnataka. Leave empty when the state "
        "charges the same amount every month.",
    )
    special_month_tax = fields.Float(
        string="Special Month Tax", default=0.0,
        help="Amount collected in the special month instead of the monthly tax.",
    )
    active = fields.Boolean(default=True)
    note = fields.Char(string="Source Note")

    @api.constrains("amount_from", "amount_to")
    def _check_band(self):
        for slab in self:
            if slab.amount_from < 0 or slab.amount_to < 0:
                raise ValidationError(_("Professional tax wage bands cannot be negative."))
            if slab.amount_to and slab.amount_to < slab.amount_from:
                raise ValidationError(_(
                    "The upper bound of a professional tax band must not be below "
                    "its lower bound."
                ))

    @api.depends("state_id", "amount_from", "amount_to", "monthly_tax")
    def _compute_display_name(self):
        for slab in self:
            upper = f"{slab.amount_to:.0f}" if slab.amount_to else _("and above")
            slab.display_name = "%s: %.0f - %s" % (
                slab.state_id.name or "", slab.amount_from, upper,
            )

    @api.model
    def _find_slab(self, state, wage, date):
        """Return the slab covering ``wage`` in ``state`` on ``date``, if any."""
        if not state:
            return self.browse()
        wage = max(wage or 0.0, 0.0)
        candidates = self.search([
            ("state_id", "=", state.id),
            ("effective_from", "<=", date),
            ("amount_from", "<=", wage),
        ], order="effective_from desc, amount_from desc")
        if not candidates:
            return self.browse()
        latest = candidates[0].effective_from
        for slab in candidates.filtered(lambda s: s.effective_from == latest):
            if not slab.amount_to or wage <= slab.amount_to:
                return slab
        return self.browse()

    @api.model
    def compute_tax(self, state, wage, date):
        """Return the professional tax due for one month.

        Zero is returned when the state has no slab table loaded or the wage
        falls below the state's exemption limit.
        """
        slab = self._find_slab(state, wage, date)
        if not slab:
            return 0.0
        if slab.special_month and int(slab.special_month) == date.month:
            return slab.special_month_tax
        return slab.monthly_tax
