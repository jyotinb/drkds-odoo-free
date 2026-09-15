from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

#: Month selection reused by the company setting and the range builder wizard.
MONTH_SELECTION = [
    ("1", "January"), ("2", "February"), ("3", "March"), ("4", "April"),
    ("5", "May"), ("6", "June"), ("7", "July"), ("8", "August"),
    ("9", "September"), ("10", "October"), ("11", "November"), ("12", "December"),
]


class ResCompany(models.Model):
    """Carries the financial year convention used by every numbering helper."""

    _inherit = "res.company"

    drkds_fy_start_month = fields.Selection(
        MONTH_SELECTION,
        string="Financial Year Starts",
        default="4",
        required=True,
        help="First month of the financial year. India uses April, so the year "
        "running 1 April 2026 to 31 March 2027 is written 2026-27. Change it "
        "only if your books genuinely close on another month.",
    )

    @api.constrains("drkds_fy_start_month")
    def _check_drkds_fy_start_month(self):
        for company in self:
            if not company.drkds_fy_start_month:
                raise ValidationError(_("A financial year start month is required."))

    # -- helpers -------------------------------------------------------
    def drkds_fy_start_year(self, date):
        """Return the calendar year the financial year containing ``date`` starts in.

        A date on or after the start month belongs to the financial year opening
        in its own calendar year; anything earlier belongs to the one opened the
        previous calendar year. With an April start, 31 March 2026 therefore
        returns 2025 and 1 April 2026 returns 2026.
        """
        self.ensure_one()
        date = fields.Date.to_date(date)
        start_month = int(self.drkds_fy_start_month or "4")
        return date.year if date.month >= start_month else date.year - 1

    def drkds_fy_string(self, date):
        """Return the financial year of ``date`` as ``2026-27``.

        This is the form GST invoice series are expected to carry, and the one
        other modules and reports should call rather than re-deriving it.
        """
        start_year = self.drkds_fy_start_year(date)
        return "%04d-%02d" % (start_year, (start_year + 1) % 100)

    def drkds_fy_short_string(self, date):
        """Return the financial year of ``date`` as ``2627``.

        The compact form used where an invoice number has to stay short.
        """
        start_year = self.drkds_fy_start_year(date)
        return "%02d%02d" % (start_year % 100, (start_year + 1) % 100)

    def drkds_fy_bounds(self, date):
        """Return ``(date_from, date_to)`` of the financial year containing ``date``.

        The last day is derived by stepping a full year forward and back one
        day, so a non-April start month and leap years both come out right.
        """
        self.ensure_one()
        start_month = int(self.drkds_fy_start_month or "4")
        date_from = fields.Date.to_date(date).replace(
            year=self.drkds_fy_start_year(date), month=start_month, day=1
        )
        return date_from, date_from + relativedelta(years=1, days=-1)
