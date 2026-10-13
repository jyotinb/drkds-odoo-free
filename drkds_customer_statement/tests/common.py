from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

REPORT_REF = "drkds_customer_statement.action_report_drkds_statement"


class StatementCase(AccountTestInvoicingCommon):
    """Shared fixtures: a customer with five invoices and two payments at fixed dates.

    All amounts are in the company currency except the last invoice, which is
    300 EUR at a rate of 2 EUR per company unit, so it posts as 150.00.

        INV1  2024-02-20  1,000.00   paid in full by PAY1 on 2024-03-05
        INV2  2024-04-05    800.00   300.00 paid by PAY2 on 2024-04-20
        INV3  2024-05-15    650.00
        INV4  2024-06-10    420.00
        INV5  2024-06-25  300 EUR = 150.00
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.eur = cls.setup_other_currency("EUR", rates=[("2024-01-01", 2.0)])
        cls.customer = cls.env["res.partner"].create({
            "name": "Meridian Traders",
            "email": "accounts@meridian.example.com",
            "is_company": True,
        })
        cls.inv1 = cls._invoice("2024-02-20", 1000.0)
        cls.inv2 = cls._invoice("2024-04-05", 800.0)
        cls.inv3 = cls._invoice("2024-05-15", 650.0)
        cls.inv4 = cls._invoice("2024-06-10", 420.0)
        cls.inv5 = cls._invoice("2024-06-25", 300.0, currency=cls.eur)
        cls.pay1 = cls._pay(cls.inv1, "2024-03-05", 1000.0)
        cls.pay2 = cls._pay(cls.inv2, "2024-04-20", 300.0)

    @classmethod
    def _invoice(cls, date, amount, partner=None, currency=None,
                 move_type="out_invoice", ref=None):
        return cls._create_invoice(
            move_type=move_type,
            invoice_date=date,
            partner_id=(partner or cls.customer).id,
            currency_id=(currency or cls.company_data["currency"]).id,
            invoice_date_due=date,
            ref=ref,
            invoice_line_ids=[(0, 0, {
                "name": "Statement test line",
                "quantity": 1.0,
                "price_unit": amount,
                "tax_ids": [(5, 0, 0)],
            })],
            post=True,
        )

    @classmethod
    def _pay(cls, invoice, date, amount):
        return cls.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=invoice.ids,
        ).create({
            "payment_date": fields.Date.to_date(date),
            "amount": amount,
        })._create_payments()

    def _data(self, date_from, date_to, statement_type="activity",
              include_vendor=False):
        return {
            "date_from": date_from,
            "date_to": date_to,
            "statement_type": statement_type,
            "include_vendor": include_vendor,
            "company_id": self.env.company.id,
        }

    def _render(self, partners, **kwargs):
        html, kind = self.env["ir.actions.report"]._render_qweb_html(
            REPORT_REF, partners.ids, data=self._data(**kwargs),
        )
        self.assertEqual(kind, "html")
        return html.decode()
