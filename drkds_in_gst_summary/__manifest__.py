{
    "name": "GST Outward and Inward Summary (India)",
    "summary": "A period GST summary by rate, by state and by HSN, for checking before you file",
    "description": """
GST Outward and Inward Summary (India)
======================================

The working paper you want open next to the return before you press submit.
Pick a period and a company, press Compute, and read three tables back.

What you get
------------
* **Outward supplies** - taxable value, CGST, SGST, IGST and cess, bucketed by
  the combined GST rate and by place of supply, with intra-state and
  inter-state separated.
* **Inward supplies** - the same breakdown for vendor bills and debit notes.
* **HSN summary** - HSN/SAC code, description, UQC, quantity, taxable value and
  tax per rate, aggregated across the whole period.
* **Reconciliation totals** - the period figures grouped the way GSTR-3B table
  3.1(a) and the GSTR-1 registered/unregistered split present them, so a
  difference shows up as a number rather than a hunch.
* **Drill-down** - every row opens the documents it was built from, so a figure
  that looks wrong can be traced to the invoice in two clicks.
* **Export** - XLSX when the standard xlsxwriter library is present, CSV
  otherwise. No extra Python package is required either way.

How the numbers are found
-------------------------
Nothing here matches on tax names. The module reads the Indian localisation's
own tax tags through ``account.tax.l10n_in_gst_tax_type``, so a tax lands in
the CGST, SGST, IGST or cess column because of how it is wired, not because of
what it is called. Place of supply is the localisation's place-of-supply field
on the document, HSN/SAC is the field on the invoice line, and the UQC is the
GST unit code on the unit of measure. Amounts come from Odoo's own tax engine,
the same code that produces the invoice totals, so the summary and the invoice
cannot disagree about rounding.

Credit notes and debit notes are subtracted, not listed separately, because
that is how they affect the supplies of a period.

Why this exists
---------------
Odoo 19 Community ships the Indian localisation's GST plumbing - the tax tags,
the place of supply, the HSN field and the GSTR section tag on invoice lines -
but no report that adds them up for a period. This module is that report.

What this is not
----------------
This is a check-before-you-file summary. It does **not** generate a GST return,
it does **not** produce a filing-ready JSON, and it makes no call to any
government portal. Treat every figure as something to compare against the
return your filing tool prepares.

Input tax credit is shown as a single inward figure and is **not** split into
eligible and ineligible. Odoo 19 Community records no ITC eligibility flag on a
tax or an account, so any such split would be invented rather than read, and an
invented ITC figure is worse than none.

This module is a tool to assist with compliance workflows. Responsibility for
statutory compliance rests with the user and their tax professional.

The drkds Accounting India app adds GSTR-1 and GSTR-3B preparation and GSTR-2A
reconciliation.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Accounting/Localizations/Reporting",
    "author": "drkds",
    "website": "https://github.com/drkds/drkds-odoo-free",
    "license": "LGPL-3",
    "depends": ["l10n_in"],
    "data": [
        "security/ir.model.access.csv",
        "views/drkds_gst_summary_views.xml",
    ],
    "images": ["static/description/cover.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
