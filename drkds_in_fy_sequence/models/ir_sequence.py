from dateutil.relativedelta import relativedelta

import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

#: Tokens this module adds on top of the ones Odoo already interpolates.
FY_TOKENS = ("fy", "fy_short", "range_fy", "range_fy_short", "current_fy", "current_fy_short")

#: Matches ``%(fy)s`` and friends inside a prefix or a suffix.
FY_TOKEN_RE = re.compile(r"%\((" + "|".join(FY_TOKENS) + r")\)s")


class IrSequence(models.Model):
    """Adds Indian financial year tokens to sequence prefixes and suffixes.

    Odoo interpolates ``%(year)s``, ``%(range_year)s`` and similar calendar
    tokens in :meth:`_get_prefix_suffix`. Those tokens are built from
    ``strftime`` codes, so a financial year spanning two calendar years cannot
    be expressed with them. Rather than reimplementing numbering, this override
    resolves the financial year tokens to plain text first and then lets the
    standard implementation interpolate everything else exactly as before.
    """

    _inherit = "ir.sequence"

    drkds_fy_company_id = fields.Many2one(
        "res.company", string="FY Convention Company", compute="_compute_drkds_fy_company_id",
        help="Company whose financial year start month is used when this "
        "sequence interpolates a financial year token.",
    )

    @api.depends("company_id")
    def _compute_drkds_fy_company_id(self):
        for sequence in self:
            sequence.drkds_fy_company_id = sequence.company_id or self.env.company

    # -- interpolation -------------------------------------------------
    def _drkds_fy_values(self, date=None, date_range=None):
        """Return the financial year token values for this sequence.

        ``date`` follows the same precedence Odoo uses: the explicit argument,
        then the ``ir_sequence_date`` context key, then today. ``date_range``
        is resolved the same way from ``ir_sequence_date_range`` so that
        ``%(range_fy)s`` reports the financial year of the subsequence the
        number is actually drawn from.
        """
        self.ensure_one()
        company = self.company_id or self.env.company
        today = fields.Date.context_today(self)
        effective = date or self.env.context.get("ir_sequence_date") or today
        ranged = date_range or self.env.context.get("ir_sequence_date_range") or today
        effective = fields.Date.to_date(effective)
        ranged = fields.Date.to_date(ranged)
        return {
            "fy": company.drkds_fy_string(effective),
            "fy_short": company.drkds_fy_short_string(effective),
            "range_fy": company.drkds_fy_string(ranged),
            "range_fy_short": company.drkds_fy_short_string(ranged),
            "current_fy": company.drkds_fy_string(today),
            "current_fy_short": company.drkds_fy_short_string(today),
        }

    def _drkds_resolve_fy_tokens(self, text, values):
        """Replace the financial year tokens in ``text`` with their values."""
        if not text:
            return text
        return FY_TOKEN_RE.sub(lambda match: values[match.group(1)], text)

    def _get_prefix_suffix(self, date=None, date_range=None):
        """Resolve financial year tokens, then defer to the standard behaviour."""
        self.ensure_one()
        if not FY_TOKEN_RE.search((self.prefix or "") + (self.suffix or "")):
            return super()._get_prefix_suffix(date=date, date_range=date_range)
        values = self._drkds_fy_values(date=date, date_range=date_range)
        resolved = self.new(
            {
                "prefix": self._drkds_resolve_fy_tokens(self.prefix, values),
                "suffix": self._drkds_resolve_fy_tokens(self.suffix, values),
            },
            origin=self,
        )
        return super(IrSequence, resolved)._get_prefix_suffix(date=date, date_range=date_range)

    # -- date ranges ---------------------------------------------------
    def drkds_build_fy_ranges(self, date_from, years=1):
        """Create the financial year subsequences covering ``years`` from ``date_from``.

        Each range runs from the first day of the financial year start month to
        the day before the next one, so the counter held by
        ``ir.sequence.date_range`` genuinely restarts at one every year. A
        financial year that already has a range is left untouched, which makes
        the action safe to re-run.

        :return: the ``ir.sequence.date_range`` records covering those years.
        """
        self.ensure_one()
        if years < 1:
            raise UserError(_("Ask for at least one financial year."))
        if not self.use_date_range:
            self.use_date_range = True
        company = self.company_id or self.env.company
        DateRange = self.env["ir.sequence.date_range"]
        ranges = DateRange.browse()
        cursor = fields.Date.to_date(date_from)
        for _index in range(years):
            start, end = company.drkds_fy_bounds(cursor)
            existing = DateRange.search(
                [
                    ("sequence_id", "=", self.id),
                    ("date_from", "<=", end),
                    ("date_to", ">=", start),
                ],
                limit=1,
            )
            if existing:
                ranges |= existing
            else:
                ranges |= DateRange.create(
                    {"sequence_id": self.id, "date_from": start, "date_to": end, "number_next": 1}
                )
            cursor = end + relativedelta(days=1)
        return ranges

    def action_drkds_open_fy_range_builder(self):
        """Open the range builder wizard preloaded with this sequence."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Build Financial Year Ranges"),
            "res_model": "drkds.fy.range.builder",
            "view_mode": "form",
            "target": "new",
            "context": {"default_sequence_id": self.id},
        }
