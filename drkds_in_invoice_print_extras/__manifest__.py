{
    "name": "Indian Invoice Print Extras",
    "summary": "Adds GST state codes, full bank and IFSC details, a declaration, a signature block and a reverse charge marker to the standard Indian invoice PDF",
    "description": """
Indian Invoice Print Extras
===========================

**Odoo's own Indian localisation already produces the GST invoice.** Install
``l10n_in`` and the standard invoice PDF is titled Tax Invoice, Bill of Supply
or Invoice-cum-Bill of Supply as the case requires, carries the HSN/SAC column,
prints the full HSN summary with the CGST/SGST, IGST and Cess split, and shows
the place of supply and the GSTINs. None of that is this module's work and this
module does not repeat it.

This module fills the small gaps that are left. It adds five blocks to that
same PDF and changes nothing else.

What it adds
------------
* **GST state codes.** The two digit code lives on the state record as
  ``l10n_in_tin`` and the localisation maintains it, but never prints it. This
  module prints it beside the supplier state, the buyer state, the shipping
  state and the place of supply, which is where an Indian reviewer looks for it.
* **A proper bank block.** The standard PDF mentions the recipient bank only as
  a phrase inside the payment terms sentence. This module prints a labelled
  block: account holder, account number, **IFSC** and **branch**. If the
  invoice carries no recipient bank, the company's own first bank account is
  used rather than printing nothing.
* **A declaration.** The customary "we declare that this invoice shows the
  actual price..." sentence, as a company setting with a sensible default. Not
  present in the standard PDF at all.
* **A signature block.** "For <company>" and "Authorised Signatory", with room
  to sign. Not present in the standard PDF at all.
* **A reverse charge marker.** ``l10n_in`` already carries a reverse charge flag
  on the tax and shows it on the tax form, but never prints it on the invoice.
  When any tax on the lines is flagged, the invoice now says so.

What it does not do
-------------------
It adds no second report, no print menu entry and no new PDF. There is one
invoice PDF and this module extends it. It touches no amount, no tax
computation and no total. It does not change how amounts are spelled in words.

Scope, honestly
---------------
This is a print-layout module. It makes the standard Indian invoice PDF more
complete for everyday use; it is not a GST compliance engine and does not claim
to be one.

This module is a tool to assist with compliance workflows. Responsibility for
statutory compliance rests with the user and their tax professional.

The drkds Accounting India app adds GSTR-1 and GSTR-3B preparation, GSTR-2A reconciliation, TDS and TCS with Form 26Q and an E-Way Bill register.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Accounting/Localizations",
    "author": "drkds",
    "website": "https://github.com/drkds/drkds-odoo-free",
    "license": "LGPL-3",
    "depends": ["l10n_in"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "report/drkds_in_invoice_print_extras_templates.xml",
    ],
    "images": ["static/description/cover.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
