{
    "name": "Proforma Invoice",
    "summary": "Issue a numbered proforma invoice from a quotation or a draft invoice, without touching your accounts",
    "description": """
Proforma Invoice
================

A proforma invoice is a commercial document that looks like an invoice but is
not one. It states what the goods or services will cost so the buyer can open a
letter of credit, clear customs, release a budget or obtain an import licence.
It must never reach the ledger, and it must never carry a tax invoice number.

This module makes that guarantee structural rather than a matter of discipline.

What it does
------------
* **Issue a proforma from a quotation or from a draft customer invoice.**
  One button on either document copies the customer, the lines, the quantities,
  the unit prices, the discounts, the taxes and the currency.
* **Its own sequence.** Proforma numbers come from a dedicated sequence with a
  ``PRO/`` prefix. Issuing a proforma never consumes an invoice number, so the
  invoice sequence stays unbroken and auditable. This is the defect in almost
  every hand-rolled proforma.
* **No accounting entry, ever.** A proforma is a stand-alone record. It is not
  an ``account.move``, it carries no journal, no account and no accounting
  lines, and nothing in it can be posted. Taxes are computed for information
  only, so the customer sees the price they will actually be charged, while no
  tax liability and no receivable is recognised.
* **A document that cannot be mistaken for an invoice.** The PDF is headed
  "Proforma Invoice" and carries a statement that it is not a tax invoice and
  confers no input tax credit. The wording is a company setting, so it can be
  matched to local practice.
* **A visible trail.** A proforma moves through draft, issued and cancelled.
  When the source quotation or draft invoice is finally invoiced for real, the
  proforma is marked converted and linked to the resulting invoice.
* **Portal and email.** A customer who can already see the quotation on the
  portal can view and download its proforma there. A mail template sends the
  document with the PDF attached.

Fields
------
Proforma number, date, validity date, customer, source document, currency,
lines copied from the source, taxes shown for information, untaxed, tax and
total amounts, payment terms wording and a free-text note printed on the PDF.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "author": "drkds",
    "website": "https://drkdsinfo.com",
    "license": "LGPL-3",
    "depends": ["sale"],
    "data": [
        "security/ir.model.access.csv",
        "security/drkds_proforma_invoice_security.xml",
        "data/ir_sequence_data.xml",
        "report/drkds_proforma_invoice_reports.xml",
        "report/drkds_proforma_invoice_templates.xml",
        "data/mail_template_data.xml",
        "views/drkds_proforma_invoice_views.xml",
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
        "views/res_config_settings_views.xml",
        "views/portal_templates.xml",
    ],
    "images": ["static/description/cover.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
