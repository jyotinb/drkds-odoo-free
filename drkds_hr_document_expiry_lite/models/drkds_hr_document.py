import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

ACTIVITY_XMLID = "drkds_hr_document_expiry_lite.mail_activity_data_document_expiry"


class DrkdsHrDocument(models.Model):
    """One document held by one employee, with its file and its expiry.

    The state is a stored computed field: Valid, Expiring once today is
    inside the type's reminder window, Expired once the expiry date has
    passed. Nothing in the ORM fires when the calendar moves, so the daily
    cron re-triggers the computation and schedules the reminders.

    Personal data stays in this database. The document number is never
    written to the log.
    """

    _name = "drkds.hr.document"
    _description = "Employee Document"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "expiry_date asc, id desc"
    _check_company_auto = True

    name = fields.Char(compute="_compute_name", store=True)
    employee_id = fields.Many2one(
        "hr.employee", string="Employee", required=True, index=True,
        ondelete="cascade", tracking=True, check_company=True,
    )
    type_id = fields.Many2one(
        "drkds.hr.document.type", string="Document Type", required=True,
        ondelete="restrict", tracking=True, check_company=True,
    )
    requires_expiry = fields.Boolean(related="type_id.requires_expiry")
    number = fields.Char(
        string="Document Number",
        help="Reference printed on the document. Kept in this database only.",
    )
    issue_date = fields.Date(string="Issue Date", tracking=True)
    expiry_date = fields.Date(string="Expiry Date", tracking=True, index=True)
    file = fields.Binary(string="File", attachment=True)
    file_name = fields.Char(string="File Name")
    note = fields.Text()
    state = fields.Selection(
        [("valid", "Valid"), ("expiring", "Expiring"), ("expired", "Expired")],
        string="Status", compute="_compute_state", store=True, tracking=True,
    )
    days_to_expiry = fields.Integer(
        string="Days Left", compute="_compute_days_to_expiry",
        help="Days from today to the expiry date; negative once expired.",
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        related="employee_id.company_id", store=True, index=True,
    )

    # -- computes -------------------------------------------------------
    def _today_by_document(self):
        """{document: today's date in its employee's timezone}.

        An expiry date is a calendar date where the employee works. The daily
        job runs as OdooBot, which has no timezone, so ``context_today`` alone
        gives the UTC date: an Indian site's job, run in the early IST hours,
        would leave a document that lapsed at midnight IST reading Expiring
        for another whole day. Every employee carries a timezone, and it gives
        the same answer whoever, or whatever, triggers the computation.
        """
        todays, result = {}, {}
        for doc in self:
            tz = doc.employee_id.tz
            if tz not in todays:
                todays[tz] = fields.Date.context_today(self.with_context(tz=tz) if tz else self)
            result[doc] = todays[tz]
        return result

    @api.depends("employee_id.name", "type_id.name")
    def _compute_name(self):
        for doc in self:
            if doc.employee_id and doc.type_id:
                doc.name = f"{doc.type_id.name} - {doc.employee_id.name}"
            else:
                doc.name = doc.type_id.name or doc.employee_id.name or ""

    def _state_at(self, today):
        """Pure state rule, shared by the compute and the cron.

        Expiring on the day the window opens, expired the day after the
        expiry date: a document expiring today is still usable today.
        """
        self.ensure_one()
        if not self.expiry_date:
            return "valid"
        if self.expiry_date < today:
            return "expired"
        if self.expiry_date - timedelta(days=self.type_id.remind_days) <= today:
            return "expiring"
        return "valid"

    @api.depends("expiry_date", "employee_id.tz", "type_id.remind_days", "type_id.requires_expiry")
    def _compute_state(self):
        todays = self._today_by_document()
        for doc in self:
            doc.state = doc._state_at(todays[doc])

    @api.depends("expiry_date", "employee_id.tz")
    def _compute_days_to_expiry(self):
        todays = self._today_by_document()
        for doc in self:
            doc.days_to_expiry = (doc.expiry_date - todays[doc]).days if doc.expiry_date else 0

    # -- constraints ----------------------------------------------------
    @api.constrains("expiry_date", "issue_date", "type_id")
    def _check_dates(self):
        for doc in self:
            if doc.type_id.requires_expiry and not doc.expiry_date:
                raise ValidationError(_(
                    "A document of type %(type)s needs an expiry date.",
                    type=doc.type_id.name,
                ))
            if doc.issue_date and doc.expiry_date and doc.expiry_date < doc.issue_date:
                raise ValidationError(_("The expiry date cannot be before the issue date."))

    # -- orm ------------------------------------------------------------
    def write(self, vals):
        if "state" in vals:
            # The status is worked out from the dates and is never taken from
            # a client: readonly in the views stops neither an RPC write nor
            # an import that updates existing documents.
            vals = {key: value for key, value in vals.items() if key != "state"}
        res = super().write(vals)
        if "expiry_date" in vals or "file" in vals:
            # A renewal: the old reminder no longer applies. If the new date
            # is still inside the window, tomorrow's cron raises a fresh one.
            self.activity_unlink([ACTIVITY_XMLID])
        return res

    # -- reminders ------------------------------------------------------
    def _can_take_reminder(self, user):
        """Whether ``user`` can act on this document's reminder: an active
        internal user with HR officer rights in the document's company.

        Anyone else would get an activity, and its notification mail, for a
        document they cannot open. Core only steers the HR Responsible picker
        to such users; nothing keeps the value valid once a user loses the
        rights or the company, or when it is set by import or RPC.
        """
        self.ensure_one()
        user = user.sudo()
        return bool(
            user
            and user.active
            and not user.share
            and user._has_group("hr.group_hr_user")
            and self.company_id in user.company_ids
        )

    def _reminder_user(self):
        """The employee's HR responsible, else the company fallback: the first
        of the two who can open the document. Empty when neither can."""
        self.ensure_one()
        for user in (
            self.employee_id.sudo().hr_responsible_id,
            self.company_id.sudo().drkds_hr_document_responsible_id,
        ):
            if self._can_take_reminder(user):
                return user
        return self.env["res.users"]

    def _schedule_expiry_activity(self):
        """Schedule one reminder per document that has none yet. Returns the
        documents that got a new activity."""
        scheduled = self.browse()
        for doc in self:
            if doc.activity_search([ACTIVITY_XMLID]):
                continue
            user = doc._reminder_user()
            if not user:
                _logger.warning(
                    "Employee document %s: neither the HR responsible nor the "
                    "fallback user is an active HR officer of its company, "
                    "reminder skipped.", doc.id,
                )
                continue
            doc.activity_schedule(
                ACTIVITY_XMLID,
                date_deadline=doc.expiry_date,
                summary=_(
                    "%(type)s of %(employee)s expires on %(date)s",
                    type=doc.type_id.name,
                    employee=doc.employee_id.name,
                    date=doc.expiry_date.strftime("%d %b %Y"),
                ),
                user_id=user.id,
            )
            scheduled |= doc
        return scheduled

    @api.model
    def _cron_refresh_states(self):
        """Daily: recompute every state against today, then remind.

        ``modified`` both marks the stored state for recomputation and drops
        the stale cached value, which ``add_to_compute`` alone would not.
        Archived documents are refreshed too, so one restored later does not
        show a status from the day it was archived. Reminders go only to
        documents still in use, held by people still employed.
        """
        docs = self.search([("expiry_date", "!=", False), ("active", "in", [True, False])])
        docs.modified(["expiry_date"])
        docs.flush_recordset(["state"])
        expiring = docs.filtered(
            lambda d: d.state == "expiring" and d.active and d.employee_id.active
        )
        scheduled = expiring._schedule_expiry_activity()
        _logger.info(
            "Employee documents refreshed: %d checked, %d expiring, %d new reminders.",
            len(docs), len(expiring), len(scheduled),
        )
        return True
