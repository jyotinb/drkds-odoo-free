{
    "name": "E-Way Bill Expiry Watch and Threshold Reminder (India)",
    "summary": "Adds an expired state, expiry filters and a threshold reminder to Odoo's e-way bill",
    "description": """
E-Way Bill Expiry Watch and Threshold Reminder (India)
======================================================

**This module does not generate e-way bills.** Odoo Community's own Indian
E-waybill module (``l10n_in_ewaybill``) does that, through the government
channel via a GSP, and it stores the e-way bill number, the date and the
validity date it gets back. Install and configure that module first; this one
is useless without it.

What Odoo's module does not do is act on the validity date it stored. Its
status is only Pending, Generated or Cancelled, it ships no scheduled action,
and its views carry no filters at all, so a bill that lapsed last night still
reads "Generated" and nobody finds out until a vehicle is stopped. This module
adds the watch on top.

What it adds
------------
* **An expiry status** - Active, Expiring Soon, Expired, Cancelled, computed
  from the validity date the portal returned. It is a **separate field**: no
  value is added to Odoo's own status selection, which is driven by API
  responses and is not ours to extend.
* **A daily scheduled action** - refreshes the expiry status, which depends on
  today's date and so cannot be triggered by any ORM dependency, and posts a
  message once on each bill that has lapsed so it surfaces without anyone
  opening it.
* **The filters and group-bys core lacks entirely** - expiring within 24
  hours, expiring within 3 days, already expired, plus group by expiry status
  and by transporter, on a proper list view with red and amber rows.
* **A threshold reminder** - posted customer invoices and credit notes at or
  above a configurable amount, 50,000 by default, with no generated e-way
  bill, as a list and an invoice filter. A reminder, never a block: nothing
  stops you posting, because exempt goods and short local movements
  legitimately carry no e-way bill.
* **A validity estimate** - one day per 200 km or part thereof under rule
  138(10), shown beside the portal's date as a sanity check, with a flag when
  the portal's validity is shorter than the rule would give. The kilometres
  per day are a company setting defaulting to 200; set 20 for over
  dimensional cargo.

What it deliberately does not do
--------------------------------
* No government API calls and no portal automation of any kind. It reads what
  Odoo's module already stored and never contacts anything.
* No manual entry of a hand-generated e-way bill number. Core owns the number,
  the date and the validity date as API results and marks them readonly;
  making them writable would let a record claim a bill the portal never issued
  and would break on the next core change. If you generate on the portal by
  hand, this module has nothing to hang a watch on.
* It never writes to a field the API owns, and never overrides core's status.

This module is a tool to assist with compliance workflows. Responsibility for
statutory compliance rests with the user and their tax professional.

The drkds Accounting India app adds e-way bill generation through the official
NIC channel, plus GSTR filing and reconciliation.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Accounting/Localizations",
    "author": "drkds",
    "website": "https://drkdsinfo.com",
    "license": "LGPL-3",
    "depends": ["l10n_in_ewaybill"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/l10n_in_ewaybill_views.xml",
        "views/account_move_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "images": ["static/description/cover.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
