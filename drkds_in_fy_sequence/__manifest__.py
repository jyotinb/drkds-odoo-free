{
    "name": "Indian Financial Year Numbering",
    "summary": "Number invoices as INV/2026-27/0001 and reset the counter every 1 April",
    "description": """
Indian Financial Year Numbering
===============================

The Indian financial year runs from 1 April to 31 March and is written
``2026-27``. GST rules expect a fresh, consecutive invoice series for each
financial year. Odoo's own sequence tokens are built from ``strftime`` codes,
so they can print a calendar year but not a year that straddles two of them.

What it adds
------------
* **A financial year token** - ``%(fy)s`` renders ``2026-27`` and
  ``%(fy_short)s`` renders ``2627``, anywhere in a sequence prefix or suffix.
  ``%(range_fy)s`` and ``%(range_fy_short)s`` report the financial year of the
  subsequence the number is drawn from, matching Odoo's ``%(range_year)s``.
* **A configurable start month** - April by default, on the company. Books that
  genuinely close on another month shift the whole calculation with one field.
* **A range builder** - an action that creates one ``ir.sequence.date_range``
  per financial year on a chosen sequence, for as many years ahead as you want.
* **A company helper** - ``company.drkds_fy_string(date)`` returns the
  financial year of any date, so reports and other modules never re-derive it.

Printing versus restarting
--------------------------
These are two different things and the module keeps them separate. Putting
``%(fy)s`` in a prefix changes what the number *looks like*; the counter keeps
climbing across the year boundary. Creating a date range per financial year is
what makes the counter genuinely restart at 1 on the first day of the year. For
a compliant series you want both, which is why the range builder exists.

Built on Odoo's own mechanism
-----------------------------
Nothing here reimplements numbering. The financial year tokens are resolved to
plain text and then handed to the standard ``_get_prefix_suffix``, and the
restart uses the stock ``use_date_range`` and ``ir.sequence.date_range``
machinery. Uninstalling leaves ordinary Odoo sequences behind.

This module is a tool to assist with compliance workflows. Responsibility for
statutory compliance rests with the user and their tax professional.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Accounting/Localizations",
    "author": "drkds",
    "website": "https://github.com/drkds/drkds-odoo-free",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_company_views.xml",
        "views/ir_sequence_views.xml",
        "wizard/drkds_fy_range_builder_views.xml",
    ],
    "images": ["static/description/cover.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
