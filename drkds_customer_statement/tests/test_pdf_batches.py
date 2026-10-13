"""Large runs are rendered in batches that wkhtmltopdf can handle."""
import io

from odoo.tests import tagged
from odoo.tools.pdf import PdfFileReader, PdfFileWriter

from odoo.addons.drkds_customer_statement.models import ir_actions_report as statement_pdf

from .common import REPORT_REF, StatementCase


@tagged("post_install", "-at_install")
class TestPdfBatches(StatementCase):
    """Three statements with a batch size of two: two wkhtmltopdf runs.

    wkhtmltopdf is replaced by a stub returning one blank page per statement,
    which is also how core splits a run per record when pages and records
    match, so no binary is needed.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.external_report_layout_id = cls.env.ref("web.external_layout_standard")
        cls.others = cls.env["res.partner"].create([
            {"name": "Batch Customer %s" % i, "is_company": True} for i in (1, 2)
        ])
        for partner in cls.others:
            cls._invoice("2024-06-10", 100.0, partner=partner)
        cls.partners = cls.customer + cls.others

    def _stub_wkhtmltopdf(self):
        runs = []

        def run_wkhtmltopdf(report_model, bodies, **kwargs):
            runs.append(len(bodies))
            writer = PdfFileWriter()
            for _body in bodies:
                writer.addBlankPage(595, 842)
            stream = io.BytesIO()
            writer.write(stream)
            return stream.getvalue()

        report_class = type(self.env["ir.actions.report"])
        self.patch(report_class, "_run_wkhtmltopdf", run_wkhtmltopdf)
        self.patch(report_class, "get_wkhtmltopdf_state", lambda report_model: "ok")
        self.patch(statement_pdf, "STATEMENTS_PER_RUN", 2)
        return runs

    def test_print_renders_in_batches(self):
        runs = self._stub_wkhtmltopdf()
        data = {
            "partner_ids": self.partners.ids, "date_from": "2024-06-01",
            "date_to": "2024-06-30", "statement_type": "activity",
            "include_vendor": False, "company_id": self.env.company.id,
        }
        pdf, kind = self.env["ir.actions.report"].with_context(
            force_report_rendering=True,
        )._render_qweb_pdf(REPORT_REF, None, data=data)
        self.assertEqual(kind, "pdf")
        self.assertEqual(runs, [2, 1])
        self.assertEqual(len(PdfFileReader(io.BytesIO(pdf)).pages), 3)

    def test_send_gets_one_pdf_per_partner_from_the_batches(self):
        runs = self._stub_wkhtmltopdf()
        pdfs = self._wizard(self.partners).with_context(
            force_report_rendering=True,
        )._render_pdfs(self.partners)
        self.assertEqual(runs, [2, 1])
        self.assertEqual(sorted(pdfs), sorted(self.partners.ids))
        for content in pdfs.values():
            self.assertEqual(len(PdfFileReader(io.BytesIO(content)).pages), 1)

    def test_small_run_stays_one_run(self):
        runs = self._stub_wkhtmltopdf()
        self._wizard(self.customer + self.others[0]).with_context(
            force_report_rendering=True,
        )._render_pdfs(self.customer + self.others[0])
        self.assertEqual(runs, [2])
