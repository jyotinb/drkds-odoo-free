from odoo import _, api, fields, models
from odoo.exceptions import UserError

#: Models this document must never touch. A proforma is a commercial
#: document, not an accounting one: it may *point at* the invoice that
#: eventually replaces it, but it may never own accounting data.
ACCOUNTING_MODELS = (
    "account.move",
    "account.move.line",
    "account.journal",
    "account.account",
    "account.payment",
)

#: The single tolerated relation to an accounting model: the read-only link to
#: the real invoice that superseded the proforma.
ACCOUNTING_LINK_FIELDS = ("invoice_id", "source_move_id")


class DrkdsProformaInvoice(models.Model):
    """A numbered proforma invoice.

    The document deliberately does not inherit ``account.move``. It owns no
    journal, no account and no accounting line, so there is no code path -
    button, server action or ORM call - that could turn it into a journal
    entry. Taxes are recomputed from the source document for display only.
    """

    _name = "drkds.proforma.invoice"
    _description = "Proforma Invoice"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"
    _rec_name = "name"

    name = fields.Char(
        string="Proforma Number", required=True, copy=False, readonly=True,
        default=lambda self: _("New"), index=True,
        help="Drawn from the dedicated proforma sequence, never from an invoice sequence.",
    )
    date = fields.Date(
        string="Proforma Date", required=True, default=fields.Date.context_today,
        tracking=True,
    )
    validity_date = fields.Date(
        string="Valid Until", tracking=True,
        help="Date after which the prices quoted on this proforma are no longer held.",
    )
    partner_id = fields.Many2one(
        "res.partner", string="Customer", required=True, tracking=True,
        help="Party the proforma is addressed to.",
    )
    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency", string="Currency", required=True,
        default=lambda self: self.env.company.currency_id,
        help="Currency of the source document. A proforma never converts amounts.",
    )
    user_id = fields.Many2one(
        "res.users", string="Salesperson", default=lambda self: self.env.user,
    )

    sale_order_id = fields.Many2one(
        "sale.order", string="Source Quotation", readonly=True, copy=False,
        ondelete="set null", index="btree_not_null",
    )
    source_move_id = fields.Many2one(
        "account.move", string="Source Draft Invoice", readonly=True, copy=False,
        ondelete="set null", index="btree_not_null",
        help="Draft customer invoice this proforma was drawn from. Reading only: "
        "the proforma never writes to it.",
    )
    invoice_id = fields.Many2one(
        "account.move", string="Final Invoice", readonly=True, copy=False,
        ondelete="set null", index="btree_not_null",
        help="Real customer invoice that superseded this proforma. Set automatically "
        "when the source document is invoiced.",
    )

    line_ids = fields.One2many(
        "drkds.proforma.invoice.line", "proforma_id", string="Lines",
        copy=True,
    )

    amount_untaxed = fields.Monetary(
        string="Untaxed Amount", compute="_compute_amounts", store=True,
        currency_field="currency_id",
    )
    amount_tax = fields.Monetary(
        string="Taxes (for information)", compute="_compute_amounts", store=True,
        currency_field="currency_id",
        help="Indicative tax amount. No tax is recognised by a proforma invoice.",
    )
    amount_total = fields.Monetary(
        string="Total", compute="_compute_amounts", store=True,
        currency_field="currency_id",
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("issued", "Issued"),
            ("cancelled", "Cancelled"),
            ("converted", "Converted"),
        ],
        string="Status", default="draft", required=True, copy=False, tracking=True,
    )

    terms = fields.Text(
        string="Terms",
        help="Payment and delivery terms printed under the totals.",
    )
    note = fields.Text(
        string="Note", help="Free text printed at the foot of the proforma.",
    )
    disclaimer = fields.Text(
        string="Disclaimer", required=True,
        default=lambda self: self.env.company.drkds_proforma_disclaimer,
        help="Statement printed prominently on the PDF. Defaults to the company "
        "setting and may be adjusted per document.",
    )

    # ------------------------------------------------------------------
    # compute
    # ------------------------------------------------------------------
    @api.depends(
        "line_ids.price_subtotal", "line_ids.price_tax", "line_ids.price_total",
    )
    def _compute_amounts(self):
        for proforma in self:
            proforma.amount_untaxed = sum(proforma.line_ids.mapped("price_subtotal"))
            proforma.amount_tax = sum(proforma.line_ids.mapped("price_tax"))
            proforma.amount_total = sum(proforma.line_ids.mapped("price_total"))

    # ------------------------------------------------------------------
    # structural guarantee
    # ------------------------------------------------------------------
    @api.model
    def _accounting_fields(self):
        """Return the names of fields on this model that point at accounting data.

        Used by the test suite to prove the model cannot hold accounting state.
        Anything returned here that is not a read-only back-link is a bug.
        """
        return [
            name for name, field in self._fields.items()
            if getattr(field, "comodel_name", None) in ACCOUNTING_MODELS
        ]

    def _assert_no_ledger_effect(self):
        """Raise if a caller tries to treat a proforma as a postable document.

        ``account.move`` exposes ``action_post``/``_post``; some automations
        call them blindly on whatever record they are handed. A proforma
        answers with a clear error instead of silently doing nothing.
        """
        raise UserError(_(
            "A proforma invoice cannot be posted. It is a commercial document "
            "and never produces an accounting entry. Invoice the source "
            "document instead."
        ))

    action_post = _assert_no_ledger_effect
    _post = _assert_no_ledger_effect

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                company_id = vals.get("company_id") or self.env.company.id
                vals["name"] = self.env["ir.sequence"].with_company(
                    company_id
                ).next_by_code("drkds.proforma.invoice") or _("New")
        return super().create(vals_list)

    def unlink(self):
        for proforma in self:
            if proforma.state == "converted":
                raise UserError(_(
                    "Proforma %s has been converted into invoice %s and is part of "
                    "the audit trail. Cancel it instead of deleting it.",
                    proforma.name, proforma.invoice_id.display_name,
                ))
        return super().unlink()

    # ------------------------------------------------------------------
    # workflow
    # ------------------------------------------------------------------
    def action_issue(self):
        """Mark the proforma as issued to the customer."""
        for proforma in self:
            if proforma.state != "draft":
                raise UserError(_("Only a draft proforma can be issued."))
            if not proforma.line_ids:
                raise UserError(_("A proforma invoice needs at least one line."))
        self.write({"state": "issued"})
        return True

    def action_cancel(self):
        """Cancel the proforma. A converted proforma keeps its trail."""
        for proforma in self:
            if proforma.state == "converted":
                raise UserError(_(
                    "Proforma %s is linked to invoice %s and cannot be cancelled.",
                    proforma.name, proforma.invoice_id.display_name,
                ))
        self.write({"state": "cancelled"})
        return True

    def action_draft(self):
        """Send a cancelled proforma back to draft."""
        for proforma in self:
            if proforma.state == "converted":
                raise UserError(_("A converted proforma cannot be reset to draft."))
        self.write({"state": "draft"})
        return True

    def _mark_converted(self, invoice):
        """Link the proforma to the real invoice that replaced it.

        Called from the standard invoicing flow. Cancelled proformas are left
        alone: they were withdrawn before the sale completed.
        """
        to_convert = self.filtered(lambda p: p.state in ("draft", "issued"))
        to_convert.write({"state": "converted", "invoice_id": invoice.id})
        for proforma in to_convert:
            proforma.message_post(body=_(
                "Converted into invoice %s.", invoice.display_name,
            ))
        return to_convert

    def action_open_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_("This proforma has not been converted yet."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.invoice_id.id,
            "view_mode": "form",
        }

    # ------------------------------------------------------------------
    # printing and sending
    # ------------------------------------------------------------------
    def _get_report_base_filename(self):
        self.ensure_one()
        return self.name

    def action_print(self):
        self.ensure_one()
        return self.env.ref(
            "drkds_proforma_invoice.action_report_drkds_proforma_invoice"
        ).report_action(self)

    def action_send_by_email(self):
        """Open the mail composer preloaded with the proforma template."""
        self.ensure_one()
        template = self.env.ref(
            "drkds_proforma_invoice.mail_template_drkds_proforma_invoice",
            raise_if_not_found=False,
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Send Proforma Invoice"),
            "res_model": "mail.compose.message",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {
                "default_model": self._name,
                "default_res_ids": self.ids,
                "default_template_id": template.id if template else False,
                "default_composition_mode": "comment",
                "force_email": True,
            },
        }

    # ------------------------------------------------------------------
    # portal
    # ------------------------------------------------------------------
    def _portal_source_order(self):
        """Return the sale order that governs portal visibility, if any."""
        self.ensure_one()
        return self.sale_order_id

    def _get_portal_url(self, **kwargs):
        self.ensure_one()
        return f"/my/proforma/{self.id}"
