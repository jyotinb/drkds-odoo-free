import base64

from odoo import _, api, fields, models
from odoo.exceptions import UserError

REPORT_REF = "drkds_customer_statement.action_report_drkds_statement"
TEMPLATE_REF = "drkds_customer_statement.mail_template_drkds_statement"


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
        self.ensure_one()
        return {
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

    def action_print(self):
        self.ensure_one()
        return self.env.ref(REPORT_REF).report_action(
            self._partners(), data=self._report_data(),
        )

    def _render_pdf(self, partner):
        self.ensure_one()
        content, _type = self.env["ir.actions.report"]._render_qweb_pdf(
            REPORT_REF, res_ids=partner.ids, data=self._report_data(),
        )
        name = _("Statement %(partner)s %(date)s.pdf",
                 partner=partner.name, date=fields.Date.to_string(self.date_to))
        return self.env["ir.attachment"].create({
            "name": name,
            "type": "binary",
            "datas": base64.b64encode(content),
            "mimetype": "application/pdf",
            "res_model": "res.partner",
            "res_id": partner.id,
        })

    def action_send(self):
        """Post the statement on each partner's chatter and email it.

        The mail template is sent through the message composer, the same path
        as "Send message" on any chatter: one message per partner with the
        PDF attached, and a notification email to the partner.
        """
        self.ensure_one()
        template = self.env.ref(TEMPLATE_REF)
        partners = self._partners()
        without_email = partners.filtered(lambda p: not p.email)
        if without_email:
            raise UserError(_(
                "No email address on: %s.",
                ", ".join(without_email.mapped("display_name")),
            ))
        render_ctx = {
            "drkds_date_from": self.date_from,
            "drkds_date_to": self.date_to,
            "drkds_statement_type": self.statement_type,
        }
        for partner in partners:
            attachment = self._render_pdf(partner)
            partner.with_context(**render_ctx).message_post_with_source(
                template,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
                attachment_ids=attachment.ids,
            )
        return {"type": "ir.actions.act_window_close"}
