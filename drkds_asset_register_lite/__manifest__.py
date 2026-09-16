{
    "name": "Fixed Asset Register (Lite)",
    "summary": "A fixed asset register with a straight line depreciation schedule, without posting entries",
    "description": """
Fixed Asset Register (Lite)
===========================

A place to record what your business owns, who holds it, and what it is worth
on paper on any given day.

Odoo 19 Community ships no fixed asset register. Most small businesses end up
keeping one in a spreadsheet: a list of assets, a straight line calculation,
and a written down value at year end for the accountant. This module is that
spreadsheet, done properly, inside Odoo.

**This register does not post to your accounts.** It computes and reports.
The depreciation journal entry stays a manual entry made by whoever closes
your books, exactly as it was before you installed this.

What it keeps
-------------
* **The asset** - description, an automatic reference, category, purchase date
  and value, salvage value, useful life, depreciation start date, location,
  custodian, supplier and the supplier's invoice reference.
* **Status** - draft while you are entering it, in service once it starts
  depreciating, and disposed or scrapped once it leaves.
* **Categories** - a class of asset carrying the useful life, the period and
  the salvage percentage proposed for new assets. Changing a category never
  rewrites an asset already entered.

The schedule
------------
* Straight line, broken into either financial years or calendar months.
* A mid-year purchase is pro-rated. Periods are measured in months, so a full
  year of a leap year is worth exactly one year of depreciation and no more.
* The final period absorbs every rounding remainder, so a schedule that runs
  its course closes on the salvage value to the cent - never a cent either
  side of it.
* The schedule is derived data. Change the useful life, the value or the start
  date and it is rebuilt from scratch; no stale line is ever left behind.
* A useful life of zero or less is refused with a message that says why.

Disposal
--------
Record the date and the proceeds. The schedule stops on that date rather than
running on to the end of a life the asset never saw out, and the gain or loss
against the written down value is shown for information.

The register report
-------------------
Choose a date and get the list: every asset, its purchase value, accumulated
depreciation and written down value as at that date, with totals. The date
does not have to be a period end - the value is pro-rated inside the period it
falls in. Filter by category, custodian or status, view it on screen or print
it as a PDF for your accountant.

Multi-company
-------------
Assets, categories and schedules are company scoped, with record rules to
match. The financial year end used to cut yearly periods is set per company.

Not in this module
------------------
Posting depreciation entries to the ledger, written down value and other
non-straight-line methods, asset revaluation, and component splitting are
deliberately not here. The drkds Accounting Pro app adds posted depreciation
entries, reducing balance and other methods, revaluation and asset components.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Accounting/Accounting",
    "author": "drkds",
    "website": "https://drkdsinfo.com",
    "support": "jyotinboghani@gmail.com",
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "data": [
        "security/drkds_asset_security.xml",
        "security/ir.model.access.csv",
        "data/drkds_asset_data.xml",
        "views/drkds_asset_category_views.xml",
        "views/drkds_asset_views.xml",
        "views/res_company_views.xml",
        "wizard/drkds_asset_disposal_wizard_views.xml",
        "wizard/drkds_asset_register_wizard_views.xml",
        "report/drkds_asset_register_report.xml",
        "views/drkds_asset_menus.xml",
    ],
    "images": ["static/description/cover.png"],
    "installable": True,
    "application": True,
    "auto_install": False,
}
