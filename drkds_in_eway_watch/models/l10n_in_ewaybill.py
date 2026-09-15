"""Expiry watch on top of Odoo's own e-way bill record.

Odoo Community's ``l10n_in_ewaybill`` generates the e-way bill through the
government channel and stores what comes back, including the validity date.
What it does not do is act on that date: its ``state`` is only pending,
generated or cancelled, it ships no scheduled action, and its views carry no
filters at all. A bill that lapsed last night still reads "Generated".

This module adds the watch. It never writes to the fields the API owns
(``name``, ``ewaybill_date``, ``ewaybill_expiry_date``) and never touches the
``state`` selection, because adding a value to a selection another module
drives from an API response is exactly the kind of thing that breaks on the
next upgrade. The expiry status lives in its own field alongside core's.
"""
import math

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.fields import Domain

#: A bill is called "expiring soon" once it has this many days or fewer left.
EXPIRING_SOON_DAYS = 1


def validity_days(distance_km, km_per_day=200):
    """Return the days of validity rule 138(10) gives for ``distance_km``.

    Rule 138(10) of the CGST Rules: for cargo other than over dimensional
    cargo an e-way bill is valid for **one day for every 200 km or part
    thereof**, counted from the time of generation. The 200 km figure replaced
    the earlier 100 km with effect from 1 January 2021, by Notification
    94/2020-Central Tax amending rule 138. Over dimensional cargo uses a much
    shorter 20 km per day.

    Sources consulted while writing this, both read on 2026-09-15: the CBIC
    e-way bill rules at https://docs.ewaybillgst.gov.in/documents/EWBRules.pdf
    and the summary of the 100 km to 200 km amendment at
    https://taxguru.in/goods-and-service-tax/validity-e-way-bill-narrowed-increasing-distance-100-km-200-km-day.html

    Because the figure has changed before and differs by cargo type, the
    kilometres per day are a company setting; 200 is only the default.

    A distance of zero or less still yields one day, which matches the portal:
    an e-way bill is never issued with no validity at all.

    This result is a **suggestion for comparison only**. The date that counts
    is whatever the portal returned in ``ewaybill_expiry_date``.
    """
    km_per_day = km_per_day or 200
    if distance_km <= 0:
        return 1
    return max(1, math.ceil(float(distance_km) / float(km_per_day)))


class L10nInEwaybill(models.Model):
    _inherit = "l10n.in.ewaybill"

    drkds_watch_status = fields.Selection(
        [
            ("pending", "Not Generated"),
            ("active", "Active"),
            ("expiring", "Expiring Soon"),
            ("expired", "Expired"),
            ("cancelled", "Cancelled"),
        ],
        string="Expiry Status", compute="_compute_drkds_watch_status",
        store=True, index=True, readonly=True,
        help="Derived from the validity date returned by the portal and from the "
        "e-way bill status. Core's own status stays Generated, because that is "
        "what the portal said when the bill was created.",
    )
    drkds_days_to_expiry = fields.Integer(
        string="Days to Expiry", compute="_compute_drkds_days_to_expiry",
        help="Days left of validity. Negative once the bill has lapsed.",
    )
    drkds_suggested_expiry = fields.Date(
        string="Suggested Valid Upto", compute="_compute_drkds_suggested_expiry",
        help="What rule 138(10) would give for the declared distance: one day per "
        "200 km or part thereof. A sanity check against the portal's date, never a "
        "replacement for it.",
    )
    drkds_validity_mismatch = fields.Boolean(
        string="Validity Differs from Rule", compute="_compute_drkds_suggested_expiry",
        search="_search_drkds_validity_mismatch",
        help="The portal's validity date is earlier than the rule 138(10) estimate "
        "for the declared distance. Usually harmless, but worth a look.",
    )
    drkds_expiry_logged = fields.Boolean(
        string="Expiry Logged", copy=False, readonly=True,
        help="Set once the scheduled action has logged that this bill lapsed, so "
        "the message is posted only once.",
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends("state", "ewaybill_expiry_date")
    def _compute_drkds_watch_status(self):
        today = fields.Date.context_today(self)
        for bill in self:
            if bill.state == "cancel":
                bill.drkds_watch_status = "cancelled"
            elif bill.state != "generated":
                bill.drkds_watch_status = "pending"
            elif not bill.ewaybill_expiry_date:
                bill.drkds_watch_status = "active"
            elif bill.ewaybill_expiry_date < today:
                bill.drkds_watch_status = "expired"
            elif (bill.ewaybill_expiry_date - today).days <= EXPIRING_SOON_DAYS:
                bill.drkds_watch_status = "expiring"
            else:
                bill.drkds_watch_status = "active"

    @api.depends("ewaybill_expiry_date")
    def _compute_drkds_days_to_expiry(self):
        today = fields.Date.context_today(self)
        for bill in self:
            bill.drkds_days_to_expiry = (
                (bill.ewaybill_expiry_date - today).days if bill.ewaybill_expiry_date else 0
            )

    @api.depends("ewaybill_date", "distance", "ewaybill_expiry_date", "company_id")
    def _compute_drkds_suggested_expiry(self):
        for bill in self:
            if not bill.ewaybill_date:
                bill.drkds_suggested_expiry = False
                bill.drkds_validity_mismatch = False
                continue
            days = validity_days(
                bill.distance or 0,
                bill.company_id.drkds_eway_km_per_day or 200,
            )
            suggested = bill.ewaybill_date + relativedelta(days=days)
            bill.drkds_suggested_expiry = suggested
            bill.drkds_validity_mismatch = bool(
                bill.ewaybill_expiry_date and bill.ewaybill_expiry_date < suggested
            )

    def _search_drkds_validity_mismatch(self, operator, value):
        """Search the mismatch flag, which is computed and not stored.

        Storing it would freeze the comparison against whatever the kilometres
        per day setting was when the bill was written; computing it on the fly
        keeps a changed setting honest. The set of generated bills is small
        enough to evaluate in Python.

        Odoo passes ``in`` and ``not in`` for boolean domains as well as ``=``
        and ``!=``, so all four are handled.
        """
        if operator in ("in", "not in"):
            values = value if isinstance(value, (list, tuple, set)) else [value]
            truthy = any(bool(item) for item in values)
            falsy = any(not bool(item) for item in values)
            if truthy and falsy:
                return Domain.TRUE
            wanted = truthy if operator == "in" else not truthy
        elif operator in ("=", "!="):
            wanted = bool(value) if operator == "=" else not bool(value)
        else:
            raise NotImplementedError("Unsupported operator %s" % operator)
        candidates = self.search([("ewaybill_expiry_date", "!=", False)])
        matching = candidates.filtered("drkds_validity_mismatch")
        if wanted:
            return Domain("id", "in", matching.ids)
        return Domain("id", "not in", matching.ids)

    # ------------------------------------------------------------------
    # Scheduled refresh
    # ------------------------------------------------------------------
    @api.model
    def _cron_drkds_refresh_watch_status(self):
        """Recompute the expiry status daily and log bills that have lapsed.

        The status depends on today's date, which no ORM dependency can
        trigger, so without this job a bill would only turn red once somebody
        happened to write to it. The chatter message is posted once per bill,
        so a lapsed e-way bill surfaces in the follower's inbox rather than
        waiting to be noticed.
        """
        watched = self.search([("state", "=", "generated")])
        if watched:
            # ``modified`` is the documented way to tell the ORM that the basis
            # of a computed field has changed underneath it: unlike
            # ``add_to_compute`` it both marks the dependent field for
            # recomputation *and* drops its stale cached value, so a status
            # already read in this transaction cannot survive the refresh.
            watched.modified(["ewaybill_expiry_date", "state"])
            watched.flush_recordset(["drkds_watch_status"])
        lapsed = watched.filtered(
            lambda bill: bill.drkds_watch_status == "expired" and not bill.drkds_expiry_logged
        )
        for bill in lapsed:
            bill.message_post(
                body=_(
                    "This e-way bill expired on %(date)s. Goods still in transit need a "
                    "fresh or extended e-way bill, which is done on the portal.",
                    date=bill.ewaybill_expiry_date,
                )
            )
        lapsed.drkds_expiry_logged = True
        return True
