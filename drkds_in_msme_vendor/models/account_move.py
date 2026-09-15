from datetime import timedelta

from odoo import api, fields, models


class AccountMove(models.Model):
    """The MSME payment clock on a vendor bill.

    The clock runs from the day of acceptance of the goods or services, which
    in practice is the bill date unless the buyer records a separate acceptance
    date after inspection. The limit is the vendor's credit period, and the
    status is derived from today against the resulting due date.

    Scope note: this is a tracking tool. It deliberately does not compute the
    section 43B(h) disallowance or the section 16 interest liability - those
    are matters for the user's tax professional.
    """

    _inherit = "account.move"

    drkds_msme_covered = fields.Boolean(
        string="MSME Vendor", related="partner_id.drkds_msme_covered",
        store=True, readonly=True,
    )
    drkds_msme_category = fields.Selection(
        related="partner_id.drkds_msme_category", string="Enterprise Category",
        store=True, readonly=True,
    )
    drkds_msme_acceptance_date = fields.Date(
        string="Acceptance Date", copy=False,
        help="Day the goods or services were accepted. Leave empty to use the "
        "bill date. Set it only where acceptance genuinely happened on a "
        "different day, for example after inspection.",
    )
    drkds_msme_due_date = fields.Date(
        string="MSME Due Date", compute="_compute_drkds_msme_due_date",
        store=True, readonly=True, copy=False,
        help="Last day on which this bill may be paid without breaching the "
        "statutory limit. Empty unless the vendor is a registered micro or "
        "small enterprise.",
    )
    drkds_msme_limit_days = fields.Integer(
        string="MSME Limit (Days)", compute="_compute_drkds_msme_due_date",
        store=True, readonly=True,
        help="Credit period applied to this bill, in days.",
    )
    drkds_msme_days_outstanding = fields.Integer(
        string="Days Outstanding", compute="_compute_drkds_msme_running",
        help="Days elapsed from acceptance to today while the bill is unpaid.",
    )
    drkds_msme_days_overdue = fields.Integer(
        string="Days Overdue", compute="_compute_drkds_msme_running",
        help="Days past the MSME due date. Zero when the bill is within limit.",
    )
    drkds_msme_status = fields.Selection(
        selection=[
            ("within", "Within Limit"),
            ("due_soon", "Due Soon"),
            ("overdue", "Overdue"),
            ("settled", "Settled"),
        ],
        string="MSME Status", compute="_compute_drkds_msme_running",
        search="_search_drkds_msme_status",
    )
    drkds_msme_fy = fields.Char(
        string="Financial Year", compute="_compute_drkds_msme_fy",
        store=True, readonly=True,
        help="Indian financial year of the bill date, running April to March.",
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _drkds_msme_base_date(self):
        """Return the day the clock starts: acceptance date, else bill date."""
        self.ensure_one()
        return self.drkds_msme_acceptance_date or self.invoice_date

    @api.model
    def _drkds_msme_fy_bounds(self, on_date):
        """Return the Indian financial year (start, end) containing ``on_date``."""
        start_year = on_date.year if on_date.month >= 4 else on_date.year - 1
        return fields.Date.to_date("%s-04-01" % start_year), fields.Date.to_date(
            "%s-03-31" % (start_year + 1)
        )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends(
        "move_type",
        "invoice_date",
        "drkds_msme_acceptance_date",
        "partner_id.drkds_msme_covered",
        "partner_id.drkds_msme_has_agreement",
        "partner_id.drkds_msme_payment_days_override",
        "company_id.drkds_msme_agreement_days",
        "company_id.drkds_msme_no_agreement_days",
    )
    def _compute_drkds_msme_due_date(self):
        for move in self:
            move.drkds_msme_due_date = False
            move.drkds_msme_limit_days = 0
            if move.move_type != "in_invoice":
                continue
            partner = move.partner_id
            if not partner or not partner.drkds_msme_covered:
                continue
            base_date = move._drkds_msme_base_date()
            if not base_date:
                continue
            days = partner._drkds_msme_payment_days(move.company_id)
            move.drkds_msme_limit_days = days
            move.drkds_msme_due_date = base_date + timedelta(days=days)

    @api.depends("invoice_date")
    def _compute_drkds_msme_fy(self):
        for move in self:
            if move.invoice_date:
                start, end = self._drkds_msme_fy_bounds(move.invoice_date)
                move.drkds_msme_fy = "%s-%s" % (start.year, str(end.year)[-2:])
            else:
                move.drkds_msme_fy = False

    @api.depends(
        "drkds_msme_due_date", "amount_residual", "state", "payment_state",
        "company_id.drkds_msme_due_soon_days",
    )
    def _compute_drkds_msme_running(self):
        today = fields.Date.context_today(self)
        for move in self:
            move.drkds_msme_days_outstanding = 0
            move.drkds_msme_days_overdue = 0
            move.drkds_msme_status = False
            due_date = move.drkds_msme_due_date
            if not due_date:
                continue
            if move.state == "posted" and move.currency_id.is_zero(move.amount_residual):
                move.drkds_msme_status = "settled"
                continue
            base_date = move._drkds_msme_base_date()
            move.drkds_msme_days_outstanding = max((today - base_date).days, 0)
            if today > due_date:
                move.drkds_msme_days_overdue = (today - due_date).days
                move.drkds_msme_status = "overdue"
            elif (due_date - today).days <= move.company_id.drkds_msme_due_soon_days:
                move.drkds_msme_status = "due_soon"
            else:
                move.drkds_msme_status = "within"

    def _search_drkds_msme_status(self, operator, value):
        """Translate an MSME status search into a domain on the stored fields.

        Odoo 19 normalises selection searches to ``in`` / ``not in`` and hands
        the values over as a set, so that is the only shape handled here.
        """
        if operator not in ("in", "not in"):
            return NotImplemented
        # The ORM works out what to flush from the original domain, in which
        # this field is not stored and so contributes nothing. Flush the stored
        # fields the substituted domain actually reads.
        self.env["account.move"].flush_model(
            ["drkds_msme_due_date", "payment_state", "state"]
        )
        values = set(value)
        today = fields.Date.context_today(self)
        tracked = [("drkds_msme_due_date", "!=", False)]
        unpaid = [("payment_state", "not in", ["paid", "reversed", "invoicing_legacy"])]
        parts = []
        if "overdue" in values:
            parts.append(tracked + unpaid + [("drkds_msme_due_date", "<", today)])
        if "settled" in values:
            parts.append(tracked + [("payment_state", "in", ["paid", "reversed"])])
        if values & {"within", "due_soon"}:
            parts.append(tracked + unpaid + [("drkds_msme_due_date", ">=", today)])
        if not parts:
            domain = [("id", "=", False)]
        else:
            domain = parts[0]
            for extra in parts[1:]:
                domain = ["|"] + domain + extra
        return ["!"] + domain if operator == "not in" else domain
