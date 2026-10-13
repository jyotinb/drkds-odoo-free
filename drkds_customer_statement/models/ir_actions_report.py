from collections import OrderedDict

from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import split_every

STATEMENT_REPORT = "drkds_customer_statement.report_drkds_statement"

#: Statements rendered per wkhtmltopdf run. Odoo moves the header and footer
#: of every record of a run into one header document that is loaded on each
#: page, so the cost grows with the square of the records: on Odoo 19 with
#: wkhtmltopdf 0.12.6 a single run crashes (error -11) between 100 and 250
#: statements, and core's invoice report does the same at 500 invoices.
STATEMENTS_PER_RUN = 50


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        """Render a large statement run in batches, one PDF stream per partner.

        Print sends the partners in ``data`` (the web client passes no record
        ids with report data); Send passes them as ``res_ids``. Either way
        the batches are made of commercial partners, which is what each
        statement is tagged with, so core can split every batch per partner.
        ``_render_qweb_pdf`` then merges the streams back into one document.
        """
        report = self._get_report(report_ref)
        if report.report_name != STATEMENT_REPORT:
            return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids)
        partner_ids = res_ids or (data or {}).get("partner_ids") or []
        partners = self.env["res.partner"].browse(partner_ids).commercial_partner_id
        if len(partners) <= STATEMENTS_PER_RUN:
            return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids)
        streams = OrderedDict()
        for batch in split_every(STATEMENTS_PER_RUN, partners.ids):
            batch_streams = super()._render_qweb_pdf_prepare_streams(
                report_ref, data, res_ids=list(batch),
            )
            if False in batch_streams:
                # Core could not tell the statements apart; merging the
                # batches would silently drop all but the last one.
                raise UserError(_(
                    "The statements could not be separated in the generated PDF. "
                    "Print fewer partners at a time."
                ))
            streams.update(batch_streams)
        return streams
