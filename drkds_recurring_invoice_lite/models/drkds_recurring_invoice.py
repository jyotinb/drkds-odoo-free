import calendar
import logging
from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

#: Upper bound on invoices one template may issue in a single catch-up run.
#: A scheduler that was off for a year on a daily template is still served in
#: four runs; a runaway loop is not.
MAX_CATCH_UP = 100

#: Context key set while the module itself writes ``next_date``. A user who
#: edits the date re-anchors the day of month; the scheduler advancing it must
#: not, or a 31st anchor would decay to the 28th after one February.
_KEEP_ANCHOR = "drkds_rcl_keep_anchor"


class DrkdsRecurringInvoice(models.Model):
    """A customer invoice kept as a template and issued on a schedule.

    The template owns nothing accounting: it is a recipe. Each run produces an
    ordinary ``account.move`` of type ``out_invoice``, linked back through
    ``recurring_id``, which takes its number from the journal like any other
    invoice.
    """

    _name = "drkds.recurring.invoice"
    _description = "Recurring Invoice Template"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "next_date, id"
    _check_company_auto = True

    reference = fields.Char(
        string="Reference", required=True, copy=False, readonly=True,
        default=lambda self: _("New"), index=True,
    )
    name = fields.Char(
        string="Name", required=True, tracking=True,
        help="What the contract is, as a human reads it: 'Office rent, Unit 4'.",
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", string="Company", required=True, index=True,
        default=lambda self: self.env.company,
    )
    partner_id = fields.Many2one(
        "res.partner", string="Customer", required=True, tracking=True,
        check_company=True,
        domain="[('company_id', 'in', (False, company_id))]",
    )
    journal_id = fields.Many2one(
        "account.journal", string="Journal", required=True, check_company=True,
        compute="_compute_journal_id", store=True, readonly=False, precompute=True,
        domain="[('type', '=', 'sale'), ('company_id', '=', company_id)]",
    )
    currency_id = fields.Many2one(
        "res.currency", string="Currency", required=True,
        compute="_compute_currency_id", store=True, readonly=False, precompute=True,
    )
    payment_term_id = fields.Many2one(
        "account.payment.term", string="Payment Terms", check_company=True,
        help="Copied onto every generated invoice. Empty means immediate.",
    )
    user_id = fields.Many2one(
        "res.users", string="Salesperson", default=lambda self: self.env.user,
        help="Set as the invoice salesperson on every generated invoice.",
    )

    interval_number = fields.Integer(
        string="Repeat Every", required=True, default=1, tracking=True,
    )
    interval_unit = fields.Selection(
        [("day", "Day(s)"), ("week", "Week(s)"), ("month", "Month(s)"), ("year", "Year(s)")],
        string="Interval Unit", required=True, default="month", tracking=True,
    )
    next_date = fields.Date(
        string="Next Invoice Date", required=True, tracking=True,
        default=fields.Date.context_today,
        help="Date of the next invoice to issue. The scheduler issues it on or "
        "after this day and then moves the date forward by one interval.",
    )
    anchor_day = fields.Integer(
        string="Anchor Day", readonly=True, copy=True,
        help="Day of month the schedule is anchored to. Taken from the next "
        "date whenever a user sets it; the scheduler keeps it when advancing.",
    )
    end_date = fields.Date(
        string="End Date", tracking=True,
        help="Last date an invoice may be issued for. Leave empty for an "
        "open-ended contract. Inclusive.",
    )
    auto_post = fields.Boolean(
        string="Post Automatically", default=False, tracking=True,
        help="Post each generated invoice at once. Otherwise it is left in "
        "draft for review.",
    )
    state = fields.Selection(
        [("draft", "Draft"), ("running", "Running"), ("paused", "Paused"), ("done", "Done")],
        string="Status", default="draft", required=True, copy=False, tracking=True,
    )
    narration = fields.Html(
        string="Terms and Conditions",
        help="Copied onto the generated invoice as its terms and conditions.",
    )
    line_ids = fields.One2many(
        "drkds.recurring.invoice.line", "recurring_id", string="Lines", copy=True,
    )

    invoice_ids = fields.One2many(
        "account.move", "recurring_id", string="Invoices", readonly=True,
    )
    invoice_count = fields.Integer(compute="_compute_invoice_stats")
    last_invoice_date = fields.Date(
        string="Last Invoice Date", compute="_compute_invoice_stats",
    )
    last_error = fields.Text(
        string="Last Scheduler Error", readonly=True, copy=False,
        help="Why the scheduler could not issue the last invoice. Cleared on "
        "the next success.",
    )

    amount_untaxed = fields.Monetary(
        string="Untaxed Amount", compute="_compute_amounts", store=True,
        currency_field="currency_id",
    )
    amount_tax = fields.Monetary(
        string="Tax", compute="_compute_amounts", store=True,
        currency_field="currency_id",
    )
    amount_total = fields.Monetary(
        string="Total", compute="_compute_amounts", store=True,
        currency_field="currency_id",
    )

    _interval_positive = models.Constraint(
        "CHECK(interval_number > 0)",
        "The interval must be at least 1.",
    )

    # ------------------------------------------------------------------
    # compute
    # ------------------------------------------------------------------
    @api.depends("company_id")
    def _compute_journal_id(self):
        for rec in self:
            if rec.journal_id and rec.journal_id.company_id == rec.company_id:
                continue
            rec.journal_id = self.env["account.journal"].search(
                [("type", "=", "sale"), ("company_id", "=", rec.company_id.id)],
                limit=1,
            )

    @api.depends("journal_id", "company_id")
    def _compute_currency_id(self):
        for rec in self:
            rec.currency_id = (
                rec.journal_id.currency_id or rec.company_id.currency_id
            )

    @api.depends("invoice_ids.state", "invoice_ids.invoice_date")
    def _compute_invoice_stats(self):
        for rec in self:
            invoices = rec.invoice_ids.filtered(lambda m: m.state != "cancel")
            rec.invoice_count = len(invoices)
            dates = [d for d in invoices.mapped("invoice_date") if d]
            rec.last_invoice_date = max(dates) if dates else False

    @api.depends("line_ids.price_subtotal", "line_ids.price_total")
    def _compute_amounts(self):
        for rec in self:
            untaxed = sum(rec.line_ids.mapped("price_subtotal"))
            total = sum(rec.line_ids.mapped("price_total"))
            rec.amount_untaxed = untaxed
            rec.amount_total = total
            rec.amount_tax = total - untaxed

    @api.constrains("next_date", "end_date")
    def _check_dates(self):
        for rec in self:
            if rec.end_date and rec.next_date and rec.end_date < rec.next_date \
                    and rec.state in ("draft", "running", "paused"):
                raise ValidationError(_(
                    "The end date (%(end)s) is before the next invoice date "
                    "(%(next)s). Nothing would ever be invoiced.",
                    end=rec.end_date, next=rec.next_date,
                ))

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("reference", _("New")) == _("New"):
                vals["reference"] = self.env["ir.sequence"].next_by_code(
                    "drkds.recurring.invoice"
                ) or _("New")
            if vals.get("next_date") and not vals.get("anchor_day"):
                vals["anchor_day"] = fields.Date.to_date(vals["next_date"]).day
        return super().create(vals_list)

    def write(self, vals):
        if "next_date" in vals and vals["next_date"] and not self.env.context.get(_KEEP_ANCHOR):
            vals = dict(vals, anchor_day=fields.Date.to_date(vals["next_date"]).day)
        return super().write(vals)

    def unlink(self):
        for rec in self:
            if rec.invoice_ids:
                raise UserError(_(
                    "%s has issued invoices and is part of their trail. Archive "
                    "it instead of deleting it.", rec.display_name,
                ))
        return super().unlink()

    @api.depends("reference", "name")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.reference} {rec.name}" if rec.name else rec.reference

    # ------------------------------------------------------------------
    # schedule arithmetic
    # ------------------------------------------------------------------
    @api.model
    def _advance_date(self, date, number, unit, anchor_day=None):
        """Return ``date`` moved forward by ``number`` ``unit``.

        Day and week intervals are plain additions. Month and year intervals
        aim at ``anchor_day`` (the day of month the schedule was set on, or
        the day of ``date``) and clamp to the last day of the target month, so
        31 January + 1 month is 28 February, and from there + 1 month with a
        31st anchor is 31 March again. 29 February + 1 year is 28 February.
        """
        if number <= 0:
            raise ValueError("interval must be positive")
        if unit == "day":
            return date + timedelta(days=number)
        if unit == "week":
            return date + timedelta(weeks=number)
        if unit == "month":
            target = date + relativedelta(months=number)
        elif unit == "year":
            target = date + relativedelta(years=number)
        else:
            raise ValueError(f"unknown interval unit {unit!r}")
        day = anchor_day or date.day
        last = calendar.monthrange(target.year, target.month)[1]
        return target.replace(day=min(day, last))

    def _next_after(self, date):
        self.ensure_one()
        return self._advance_date(
            date, self.interval_number, self.interval_unit, self.anchor_day or None,
        )

    # ------------------------------------------------------------------
    # workflow buttons
    # ------------------------------------------------------------------
    def action_start(self):
        for rec in self:
            if rec.state not in ("draft", "paused"):
                raise UserError(_("Only a draft or paused template can be started."))
            if not rec.line_ids.filtered(lambda l: not l.display_type):
                raise UserError(_("Add at least one invoice line before starting."))
        self.write({"state": "running"})
        return True

    def action_pause(self):
        for rec in self:
            if rec.state != "running":
                raise UserError(_("Only a running template can be paused."))
        self.write({"state": "paused"})
        return True

    def action_done(self):
        """Close the contract by hand. Issued invoices are untouched."""
        self.write({"state": "done"})
        return True

    def action_draft(self):
        for rec in self:
            if rec.state != "done":
                raise UserError(_("Only a finished template can be reset to draft."))
        self.write({"state": "draft"})
        return True

    def action_generate_now(self):
        """Issue the invoice for the next scheduled date straight away.

        Works on a running or paused template. The same idempotency rule as
        the scheduler applies: pressing it twice does not produce a second
        invoice for the same date, only moves on to the next one.
        """
        self.ensure_one()
        if self.state not in ("running", "paused"):
            raise UserError(_("Start the template before generating an invoice."))
        if self.end_date and self.next_date > self.end_date:
            self.write({"state": "done"})
            raise UserError(_(
                "The next date %s is past the end date %s; the template has "
                "been marked done.", self.next_date, self.end_date,
            ))
        date = self.next_date
        invoice = self._generate_for_date(date) or self._existing_invoice_for(date)
        self._advance_after_generation()
        return self.action_view_invoices(invoice)

    def action_view_invoices(self, invoices=None):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        invoices = invoices if invoices is not None else self.invoice_ids
        action["domain"] = [("recurring_id", "=", self.id)]
        action["context"] = {
            "default_move_type": "out_invoice",
            "default_partner_id": self.partner_id.id,
            "create": False,
        }
        if len(invoices) == 1:
            action["views"] = [(self.env.ref("account.view_move_form").id, "form")]
            action["res_id"] = invoices.id
        return action

    # ------------------------------------------------------------------
    # generation
    # ------------------------------------------------------------------
    def _existing_invoice_for(self, date):
        self.ensure_one()
        return self.env["account.move"].search([
            ("recurring_id", "=", self.id),
            ("invoice_date", "=", date),
            ("state", "!=", "cancel"),
        ], limit=1)

    def _prepare_invoice_vals(self, date):
        self.ensure_one()
        return {
            "move_type": "out_invoice",
            "company_id": self.company_id.id,
            "partner_id": self.partner_id.id,
            "journal_id": self.journal_id.id,
            "currency_id": self.currency_id.id,
            "invoice_date": date,
            "invoice_payment_term_id": self.payment_term_id.id,
            "invoice_user_id": self.user_id.id,
            "invoice_origin": self.reference,
            "narration": self.narration,
            "recurring_id": self.id,
            "invoice_line_ids": [
                Command.create(line._prepare_invoice_line_vals()) for line in self.line_ids
            ],
        }

    def _generate_for_date(self, date):
        """Create (and optionally post) the invoice dated ``date``.

        Returns the new invoice, or an empty recordset when one already
        exists for that date, so a second call is harmless.
        """
        self.ensure_one()
        if self._existing_invoice_for(date):
            return self.env["account.move"]
        invoice = self.env["account.move"].with_company(self.company_id).create(
            self._prepare_invoice_vals(date)
        )
        if self.auto_post:
            invoice.action_post()
        self.message_post(body=_(
            "Invoice %s issued for %s.", invoice._get_html_link(), date,
        ))
        return invoice

    def _advance_after_generation(self):
        """Move ``next_date`` one interval on, closing the template past its end."""
        self.ensure_one()
        new_date = self._next_after(self.next_date)
        vals = {"next_date": new_date, "last_error": False}
        if self.end_date and new_date > self.end_date:
            vals["state"] = "done"
        self.with_context(**{_KEEP_ANCHOR: True}).write(vals)

    def _process_due(self, today):
        """Issue every invoice due on or before ``today`` for this template.

        A template whose scheduler missed several dates gets one invoice per
        missed date, in order, each on its own scheduled date. Stops at the
        end date, at a date in the future or at the safety cap.
        """
        self.ensure_one()
        created = self.env["account.move"]
        for _i in range(MAX_CATCH_UP):
            if self.state != "running" or self.next_date > today:
                break
            if self.end_date and self.next_date > self.end_date:
                self.write({"state": "done"})
                break
            created |= self._generate_for_date(self.next_date)
            self._advance_after_generation()
        return created

    @api.model
    def _cron_generate_invoices(self, today=None):
        """Daily job. Each template is isolated in its own savepoint, so one
        failing template (a missing account, a blocked posting) is logged and
        recorded on the template without stopping the others."""
        today = today or fields.Date.context_today(self)
        due = self.search([
            ("state", "=", "running"), ("next_date", "<=", today),
        ])
        created = self.env["account.move"]
        for template in due:
            try:
                with self.env.cr.savepoint():
                    created |= template._process_due(today)
            except Exception as exc:  # noqa: BLE001 - must keep serving other templates
                _logger.exception(
                    "Recurring invoice %s: generation failed", template.reference,
                )
                template.write({"last_error": str(exc)})
        return created
