{
    "name": "MSME Vendor Payment Tracking (India)",
    "summary": "Flag micro and small vendors, watch the 45 day payment clock and list what is overdue",
    "description": """
MSME Vendor Payment Tracking (India)
====================================

Section 43B(h) of the Income Tax Act, 1961 disallows the deduction for an
expense owed to a **micro or small** enterprise until the amount is actually
paid, if it was not paid inside the limitation period of section 15 of the
MSMED Act, 2006. That period is the period agreed in writing, capped at
**45 days** from the day of acceptance, or **15 days** where there is no
written agreement.

The hard part is not the arithmetic, it is knowing which bills are on the
clock at all. This module answers that, every day, without a spreadsheet.

What it does
------------
* **Vendor MSME record** - registered flag, Udyam registration number validated
  against the published ``UDYAM-XX-00-0000000`` format, enterprise category and
  registration date.
* **Micro and small only** - a medium enterprise is registered under the MSMED
  Act and appears on Udyam, but section 15 does not cover it. Medium vendors
  are shown as out of scope and their bills are never tracked. Getting this
  wrong is the most common mistake in MSME tracking.
* **Both statutory periods** - 45 days where a payment agreement is in writing,
  15 days where it is not. The basis defaults per vendor and the day counts are
  company settings, not constants, so a company can run a stricter internal
  policy. Neither may be set longer than the statute allows.
* **The clock on the bill** - MSME due date computed from the acceptance date,
  or the bill date where acceptance is the same day, plus days outstanding and
  a status of Within Limit, Due Soon or Overdue.
* **A loud warning** - an overdue bill from a micro or small vendor carries a
  red banner on the form, naming the due date and the days lost.
* **The report the auditor asks for** - outstanding MSME payments grouped by
  vendor with ageing buckets, as a list, a pivot and a graph, with a one click
  filter for bills that breach the limit inside the current Indian financial
  year.

Deliberately out of scope
-------------------------
No disallowance figure and no section 16 interest calculation are produced.
Those depend on the year of actual payment, on the accounting method and on
positions your tax adviser takes. This module tracks the clock and hands you
the evidence; the tax treatment is a matter for your tax professional.

There are no government portal calls of any kind. Udyam numbers are validated
for structure only, offline.

This module is a tool to assist with compliance workflows. Responsibility for
statutory compliance rests with the user and their tax professional.

The drkds GST suite adds GSTR-1 and GSTR-3B preparation, GSTR-2A
reconciliation and an e-invoice workflow.

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
        "views/res_partner_views.xml",
        "views/account_move_views.xml",
        "views/drkds_msme_outstanding_report_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "images": ["static/description/cover.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
