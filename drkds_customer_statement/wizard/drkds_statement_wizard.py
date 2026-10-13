from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, UserError

REPORT_REF = "drkds_customer_statement.action_report_drkds_statement"
TEMPLATE_REF = "drkds_customer_statement.mail_template_drkds_statement"
SEND_GROUP = "account.group_account_invoice"


class DrkdsStatementWizard(models.TransientModel):
    """Choose the period and the kind of statement, then print or send it."""

    _name = "drkds.statement.wizard"
    _description = "Statement of Account"

    partner_ids = fields.Many2many(
        "res.partner", string="Partners", required=True,
        default=lambda self: self._default_partner_ids(),
    )
    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(
        string="From", required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(
        string="To", required=True, default=fields.Date.context_today,
    )
    statement_type = fields.Selection(
        [("activity", "Activity"), ("outstanding", "Outstanding only")],
        string="Statement Type", required=True, default="activity",
        help="Activity: every posted movement in the period, with the balance "
        "brought forward. Outstanding only: items still open at the end "
        "date, at the amount open then.",
    )
    include_vendor = fields.Boolean(
        string="Include Vendor Side",
        help="Also list vendor bills and payments, so a partner who is both "
        "customer and supplier gets one net statement.",
    )

    @api.model
    def _default_partner_ids(self):
        if self.env.context.get("active_model") == "res.partner":
            return [(6, 0, self.env.context.get("active_ids", []))]
        return False

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for wizard in self:
            if wizard.date_from > wizard.date_to:
                raise UserError(_("The start date must not be after the end date."))

    def _report_data(self):
        """Everything the report needs, partners included.

        The web client sends a report action that carries ``data`` without
        any record ids, so the partners must travel in the data themselves.
        """
        self.ensure_one()
        return {
            "partner_ids": self._partners().ids,
            "date_from": fields.Date.to_string(self.date_from),
            "date_to": fields.Date.to_string(self.date_to),
            "statement_type": self.statement_type,
            "include_vendor": self.include_vendor,
            "company_id": self.company_id.id,
        }

    def _partners(self):
        """Statements go to commercial entities; a contact rolls up to its company."""
        partners = self.partner_ids.commercial_partner_id
        if not partners:
            raise UserError(_("Select at least one partner."))
        return partners

    def _recipients(self):
        """The contacts selected, grouped under the entity whose statement they get.

        Selecting the company emails the company; selecting a person at the
        company emails that person the company's statement.
        """
        recipients = {}
        for contact in self.partner_ids:
            commercial = contact.commercial_partner_id
            recipients[commercial] = recipients.get(commercial, contact.browse()) | contact
        return recipients

    def action_print(self):
        self.ensure_one()
        return self.env.ref(REPORT_REF).report_action(
            self._partners(), data=self._report_data(),
        )

    def _render_pdfs(self, partners):
        """Render every statement in one run and split it into one PDF per partner.

        One wkhtmltopdf run per partner costs seconds each, which a request
        for a few dozen customers cannot afford.
        """
        self.ensure_one()
        report = self.env["ir.actions.report"]
        content, report_type = report._pre_render_qweb_pdf(
            REPORT_REF, res_ids=partners.ids, data=self._report_data(),
        )
        pdfs = report._get_splitted_report(REPORT_REF, content, report_type)
        missing = partners.filtered(lambda partner: partner.id not in pdfs)
        if missing:
            raise UserError(_(
                "The statement of %s could not be found in the generated PDF.",
                ", ".join(missing.mapped("display_name")),
            ))
        return pdfs

    def _attachment_name(self, partner):
        return _("Statement %(partner)s %(date)s.pdf",
                 partner=partner.name, date=fields.Date.to_string(self.date_to))

    def action_send(self):
        """Email each statement to the contacts selected and log it on the chatter.

        One message per partner, on the company's chatter, with the PDF
        attached and the selected contacts as its only recipients. It is
        posted as a note so that followers of the contact (salespeople, for
        instance) are not mailed the customer's account.
        """
        self.ensure_one()
        if not self.env.user.has_group(SEND_GROUP):
            raise AccessError(_("Sending statements needs the Invoicing access right."))
        partners = self._partners()
        recipients = self._recipients()
        without_email = self.partner_ids.filtered(lambda contact: not contact.email)
        if without_email:
            raise UserError(_(
                "No email address on: %s.",
                ", ".join(without_email.mapped("display_name")),
            ))
        # Rendered with the user's own rights: they only see what they may read.
        pdfs = self._render_pdfs(partners)
        template = self.env.ref(TEMPLATE_REF)
        render_ctx = {
            "drkds_date_from": self.date_from,
            "drkds_date_to": self.date_to,
            "drkds_statement_type": self.statement_type,
        }
        for partner in partners:
            # Attaching and posting on a contact need write access on
            # contacts, which an Invoicing user does not get by default. The
            # right to send was checked above; sudo keeps the user as author.
            partner_sudo = partner.sudo()
            attachment = self.env["ir.attachment"].sudo().create({
                "name": self._attachment_name(partner),
                "type": "binary",
                "raw": pdfs[partner.id],
                "mimetype": "application/pdf",
                "res_model": "res.partner",
                "res_id": partner.id,
            })
            partner_sudo.with_company(self.company_id).with_context(
                **render_ctx,
            ).message_post_with_source(
                template,
                message_type="comment",
                subtype_xmlid="mail.mt_note",
                partner_ids=[Command.set(recipients[partner].ids)],
                attachment_ids=attachment.ids,
            )
        return {"type": "ir.actions.act_window_close"}
