{
    "name": "UPI Payment QR on Invoices (India)",
    "summary": "Print a scannable UPI QR code on the customer invoice, pre-filled with the amount due",
    "description": """
UPI Payment QR on Invoices (India)
==================================

Puts a UPI QR code on the customer invoice PDF and on the customer portal
page, pre-filled with the amount still due. The customer opens any UPI
application, scans, and pays. Nothing is typed, so nothing is mistyped.

What you get
------------
* **A QR code on the invoice PDF**, next to the payment block, with your UPI
  ID printed underneath for anyone who would rather type it.
* **The same QR code on the customer portal**, above the invoice preview.
* **The amount pre-filled** from the residual, so a partly paid invoice asks
  for the balance and not the original total.
* **The invoice reference carried into the payment**, as both the UPI
  transaction note and the transaction reference, which is what makes an
  incoming credit easy to match.
* **A validated UPI ID.** The company setting is checked for the
  ``name@handle`` shape on save, with a message that says what is wrong.
* **Nothing printed where it should not be.** Never on a vendor bill, never
  on a credit note, never on a draft, never on a fully paid invoice, and
  never when no UPI ID is configured.

How it is built
---------------
The link follows the NPCI UPI Linking Specifications for deep linking:
``upi://pay?pa=<vpa>&pn=<payee>&am=<amount>&cu=INR&tn=<note>&tr=<ref>``, with
every value percent-encoded. The image is rendered by Odoo's own barcode
helper, so the module adds no Python dependency and no bundled QR library.

Two switches control the payload: one to embed the amount, one to embed the
invoice reference. With the amount switch off you get an open QR code the
customer types an amount into, which suits a deposit or a part payment.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Accounting/Localizations",
    "author": "drkds",
    "website": "https://github.com/drkds/drkds-odoo-free",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/report_invoice.xml",
        "views/account_portal_templates.xml",
    ],
    "images": ["static/description/cover.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
