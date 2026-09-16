import calendar
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

#: Fields that invalidate an existing schedule when they change.
SCHEDULE_TRIGGERS = (
    "purchase_value",
    "salvage_value",
    "useful_life_value",
    "useful_life_unit",
    "depreciation_start_date",
    "period_type",
    "disposal_date",
    "state",
    "company_id",
)


def month_span(start, end):
    """Return the length of the inclusive range ``start``..``end`` in months.

    A whole calendar month counts as exactly ``1.0``; a partial one counts as
    the covered days over the length of that particular month. Measuring in
    months rather than days is what makes a straight line schedule land on
    round figures: twelve months of a leap year and of an ordinary year are
    both worth exactly one year of depreciation.
    """
    if not start or not end or end < start:
        return 0.0
    total = 0.0
    cursor = start
    while cursor <= end:
        days_in_month = calendar.monthrange(cursor.year, cursor.month)[1]
        month_end = date(cursor.year, cursor.month, days_in_month)
        segment_end = min(month_end, end)
        total += ((segment_end - cursor).days + 1) / days_in_month
        cursor = month_end + timedelta(days=1)
    return total


def fiscal_year_end(day, last_month, last_day):
    """Return the first financial year end falling on or after ``day``."""
    for year in (day.year, day.year + 1):
        clamped = min(last_day, calendar.monthrange(year, last_month)[1])
        candidate = date(year, last_month, clamped)
        if candidate >= day:
            return candidate
    # Unreachable for sane inputs, but never return None from a loop.
    return date(day.year + 1, last_month, 1)


class DrkdsAsset(models.Model):
    """A fixed asset and its straight line depreciation schedule.

    The register is deliberately informational. It computes what an asset is
    worth on paper and shows how it got there; it never writes a journal entry.
    """

    _name = "drkds.lite.asset"
    _description = "Fixed Asset"
    _order = "code desc, id desc"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(
        string="Reference", required=True, copy=False, readonly=True,
        default=lambda self: _("New"),
        help="Allocated from a sequence when the asset is created.",
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related="company_id.currency_id", string="Currency")
    category_id = fields.Many2one(
        "drkds.lite.asset.category", string="Category", required=True, tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("running", "Running"),
            ("disposed", "Disposed"),
            ("scrapped", "Scrapped"),
        ],
        default="draft", required=True, tracking=True, copy=False,
    )

    # -- acquisition ---------------------------------------------------
    purchase_date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    purchase_value = fields.Monetary(required=True, tracking=True)
    salvage_value = fields.Monetary(
        string="Salvage Value", tracking=True,
        help="Value the asset is expected to retain at the end of its life. "
             "The schedule closes exactly on this figure.",
    )
    supplier_id = fields.Many2one("res.partner", string="Supplier")
    invoice_reference = fields.Char(string="Invoice Reference")

    # -- depreciation inputs -------------------------------------------
    useful_life_unit = fields.Selection(
        [("year", "Years"), ("month", "Months")],
        string="Useful Life Unit", required=True, default="year",
    )
    useful_life_value = fields.Integer(string="Useful Life", required=True, default=5)
    useful_life_months = fields.Integer(
        compute="_compute_useful_life_months", store=True,
        help="Useful life normalised to months, which is what the schedule works in.",
    )
    period_type = fields.Selection(
        [("year", "Yearly"), ("month", "Monthly")],
        string="Period", required=True, default="year",
    )
    depreciation_start_date = fields.Date(
        required=True, default=fields.Date.context_today, tracking=True,
        help="Date depreciation begins, usually the date the asset was put to use.",
    )
    depreciation_end_date = fields.Date(
        compute="_compute_depreciation_end_date", store=True,
        help="Last day of the useful life.",
    )

    # -- custody --------------------------------------------------------
    location = fields.Char(help="Where the asset physically sits.")
    custodian_id = fields.Many2one(
        "res.partner", string="Custodian",
        help="Person answerable for the asset.",
    )

    # -- disposal -------------------------------------------------------
    disposal_date = fields.Date(copy=False, tracking=True)
    disposal_proceeds = fields.Monetary(copy=False, tracking=True)
    disposal_gain = fields.Monetary(
        string="Gain / Loss on Disposal", compute="_compute_disposal_gain", store=True,
        help="Proceeds less the written down value on the disposal date. "
             "Informational only; nothing is posted to the accounts.",
    )

    # -- schedule -------------------------------------------------------
    depreciation_line_ids = fields.One2many(
        "drkds.asset.depreciation.line", "asset_id",
        string="Depreciation Schedule", readonly=True, copy=False,
    )
    depreciation_total = fields.Monetary(
        string="Total Depreciation", compute="_compute_totals", store=True,
    )
    closing_value = fields.Monetary(
        string="Final Written Down Value", compute="_compute_totals", store=True,
    )
    value_residual = fields.Monetary(
        string="Written Down Value Today", compute="_compute_value_residual",
        help="Book value as at today, pro-rated inside the current period.",
    )

    _code_company_uniq = models.Constraint(
        "unique(code, company_id)",
        "An asset with this reference already exists for this company.",
    )

    # ------------------------------------------------------------------
    # compute
    # ------------------------------------------------------------------
    @api.depends("useful_life_value", "useful_life_unit")
    def _compute_useful_life_months(self):
        for asset in self:
            factor = 12 if asset.useful_life_unit == "year" else 1
            asset.useful_life_months = (asset.useful_life_value or 0) * factor

    @api.depends("depreciation_start_date", "useful_life_months")
    def _compute_depreciation_end_date(self):
        for asset in self:
            start = asset.depreciation_start_date
            if start and asset.useful_life_months > 0:
                asset.depreciation_end_date = (
                    start + relativedelta(months=asset.useful_life_months) - timedelta(days=1)
                )
            else:
                asset.depreciation_end_date = False

    @api.depends("depreciation_line_ids.depreciation", "depreciation_line_ids.closing_value")
    def _compute_totals(self):
        for asset in self:
            lines = asset.depreciation_line_ids.sorted("sequence")
            asset.depreciation_total = sum(lines.mapped("depreciation"))
            asset.closing_value = lines[-1].closing_value if lines else asset.purchase_value

    @api.depends("disposal_date", "disposal_proceeds", "depreciation_line_ids.closing_value")
    def _compute_disposal_gain(self):
        for asset in self:
            if asset.disposal_date and asset.state in ("disposed", "scrapped"):
                asset.disposal_gain = asset.disposal_proceeds - asset._wdv_as_at(asset.disposal_date)
            else:
                asset.disposal_gain = 0.0

    def _compute_value_residual(self):
        today = fields.Date.context_today(self)
        for asset in self:
            asset.value_residual = asset._wdv_as_at(today)

    # ------------------------------------------------------------------
    # constraints
    # ------------------------------------------------------------------
    @api.constrains("useful_life_value", "useful_life_unit")
    def _check_useful_life(self):
        for asset in self:
            if asset.useful_life_value <= 0:
                raise ValidationError(
                    _(
                        "The useful life of asset %s must be greater than zero. "
                        "An asset with no life cannot be depreciated.",
                        asset.name or _("New"),
                    )
                )

    @api.constrains("purchase_value", "salvage_value")
    def _check_values(self):
        for asset in self:
            if asset.purchase_value < 0:
                raise ValidationError(_("The purchase value cannot be negative."))
            if asset.salvage_value < 0:
                raise ValidationError(_("The salvage value cannot be negative."))
            if asset.salvage_value > asset.purchase_value:
                raise ValidationError(
                    _("The salvage value of %s cannot exceed its purchase value.", asset.name)
                )

    @api.constrains("disposal_date", "depreciation_start_date")
    def _check_disposal_date(self):
        for asset in self:
            if asset.disposal_date and asset.depreciation_start_date:
                if asset.disposal_date < asset.depreciation_start_date:
                    raise ValidationError(
                        _("The disposal date cannot fall before depreciation starts.")
                    )

    # ------------------------------------------------------------------
    # onchange
    # ------------------------------------------------------------------
    @api.onchange("category_id")
    def _onchange_category_id(self):
        category = self.category_id
        if not category:
            return
        self.useful_life_unit = category.useful_life_unit
        self.useful_life_value = category.useful_life_value
        self.period_type = category.period_type
        if category.salvage_percent and self.purchase_value:
            self.salvage_value = self.purchase_value * category.salvage_percent / 100.0

    # ------------------------------------------------------------------
    # orm
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals["code"] == _("New"):
                company_id = vals.get("company_id") or self.env.company.id
                vals["code"] = self.env["ir.sequence"].with_company(company_id).next_by_code(
                    "drkds.lite.asset"
                ) or _("New")
        assets = super().create(vals_list)
        assets._build_schedule()
        return assets

    def write(self, vals):
        result = super().write(vals)
        if any(field in vals for field in SCHEDULE_TRIGGERS):
            self._build_schedule()
        return result

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        for vals in vals_list:
            vals.setdefault("name", _("%s (copy)", self.name))
        return vals_list

    # ------------------------------------------------------------------
    # schedule
    # ------------------------------------------------------------------
    def _schedule_periods(self, start, end):
        """Yield ``(date_from, date_to)`` period boundaries covering the life."""
        self.ensure_one()
        company = self.company_id or self.env.company
        last_month = int(company.drkds_asset_fy_last_month or "3")
        last_day = company.drkds_asset_fy_last_day or 31
        cursor = start
        while cursor <= end:
            if self.period_type == "month":
                days = calendar.monthrange(cursor.year, cursor.month)[1]
                period_end = date(cursor.year, cursor.month, days)
            else:
                period_end = fiscal_year_end(cursor, last_month, last_day)
            yield cursor, min(period_end, end)
            cursor = period_end + timedelta(days=1)

    def _schedule_values(self):
        """Return the schedule of this asset as a list of line value dicts.

        The last period absorbs every rounding remainder, so the closing value
        of a schedule that runs its full course is the salvage value to the
        cent, never a cent either side of it.
        """
        self.ensure_one()
        start = self.depreciation_start_date
        life_end = self.depreciation_end_date
        if not start or not life_end or self.useful_life_months <= 0:
            return []
        depreciable = self.purchase_value - self.salvage_value
        if depreciable <= 0:
            return []

        truncated = bool(self.disposal_date) and self.state in ("disposed", "scrapped")
        end = min(life_end, self.disposal_date) if truncated else life_end
        if end < start:
            return []
        total_months = month_span(start, life_end)
        if not total_months:
            return []

        currency = self.currency_id or self.env.company.currency_id
        periods = list(self._schedule_periods(start, end))
        values = []
        accumulated = 0.0
        for index, (date_from, date_to) in enumerate(periods, start=1):
            if index == len(periods) and not truncated:
                amount = depreciable - accumulated
            else:
                share = month_span(date_from, date_to) / total_months
                amount = currency.round(depreciable * share)
            opening = self.purchase_value - accumulated
            accumulated += amount
            values.append({
                "sequence": index,
                "date_from": date_from,
                "date_to": date_to,
                "opening_value": opening,
                "depreciation": amount,
                "accumulated_depreciation": accumulated,
                "closing_value": self.purchase_value - accumulated,
            })
        return values

    def _build_schedule(self):
        """Rebuild the schedule from scratch, leaving no stale line behind."""
        Line = self.env["drkds.asset.depreciation.line"]
        for asset in self:
            asset.depreciation_line_ids.unlink()
            values = asset._schedule_values()
            if values:
                Line.create([dict(vals, asset_id=asset.id) for vals in values])
        return True

    def action_recompute_schedule(self):
        self._build_schedule()
        return True

    # ------------------------------------------------------------------
    # valuation
    # ------------------------------------------------------------------
    def _wdv_as_at(self, as_at):
        """Return the written down value of this asset on ``as_at``.

        Periods that closed on or before the date count in full; the period the
        date falls inside is pro-rated by the months elapsed within it.
        """
        self.ensure_one()
        if not as_at or self.state == "draft":
            return self.purchase_value
        if not self.depreciation_start_date or as_at < self.depreciation_start_date:
            return self.purchase_value
        accumulated = 0.0
        for line in self.depreciation_line_ids.sorted("sequence"):
            if line.date_to <= as_at:
                accumulated += line.depreciation
            elif line.date_from <= as_at:
                full = month_span(line.date_from, line.date_to)
                elapsed = month_span(line.date_from, as_at)
                if full:
                    accumulated += line.depreciation * elapsed / full
                break
            else:
                break
        currency = self.currency_id or self.env.company.currency_id
        return currency.round(self.purchase_value - accumulated)

    # ------------------------------------------------------------------
    # workflow
    # ------------------------------------------------------------------
    def action_confirm(self):
        for asset in self:
            if asset.state != "draft":
                raise UserError(_("Only a draft asset can be put into service."))
            if asset.useful_life_months <= 0:
                raise UserError(_("Set a useful life greater than zero before starting %s.", asset.name))
        self.write({"state": "running"})
        return True

    def action_set_draft(self):
        self.write({
            "state": "draft",
            "disposal_date": False,
            "disposal_proceeds": 0.0,
        })
        return True

    def action_open_disposal_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Dispose Asset"),
            "res_model": "drkds.asset.disposal.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_asset_id": self.id},
        }

    def action_dispose(self, disposal_date=None, proceeds=0.0, scrapped=False):
        """Close an asset off at ``disposal_date``.

        The schedule is truncated at that date, so accumulated depreciation
        stops where the asset left the business rather than running on to the
        end of a life it never saw out.
        """
        for asset in self:
            if asset.state not in ("running", "draft"):
                raise UserError(_("Asset %s has already been closed off.", asset.code))
            asset.write({
                "state": "scrapped" if scrapped else "disposed",
                "disposal_date": disposal_date or fields.Date.context_today(asset),
                "disposal_proceeds": 0.0 if scrapped else proceeds,
            })
        return True
