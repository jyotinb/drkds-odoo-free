from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DrkdsStatementReport(models.AbstractModel):
    """Builds the values for one statement per partner.

    The period, the statement type and the partners travel in ``data`` from
    the wizard; the report action itself is bound to ``res.partner``.

    When a report action carries ``data``, the web client requests
    ``/report/pdf/<report>?options=...`` without record ids, so ``docids``
    is ``None`` on Print and the partners come from ``data["partner_ids"]``.
    Server-side renders (Send by Email) pass the ids explicitly.
    """

    _name = "report.drkds_customer_statement.report_drkds_statement"
    _description = "Statement of Account Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        if not data.get("date_to"):
            raise UserError(_("Print the statement from the Statement wizard, "
                              "which sets the period."))
        date_to = fields.Date.to_date(data["date_to"])
        date_from = fields.Date.to_date(data.get("date_from") or date_to)
        company = self.env["res.company"].browse(
            data.get("company_id") or self.env.company.id
        )
        partner_ids = docids or data.get("partner_ids") or []
        partners = self.env["res.partner"].browse(partner_ids).commercial_partner_id
        statements = [
            partner._drkds_statement_data(
                date_from, date_to,
                statement_type=data.get("statement_type", "activity"),
                include_vendor=bool(data.get("include_vendor")),
                company=company,
            )
            for partner in partners
        ]
        return {
            "doc_ids": partners.ids,
            "doc_model": "res.partner",
            "docs": partners,
            "statements": statements,
            "data": data,
        }
