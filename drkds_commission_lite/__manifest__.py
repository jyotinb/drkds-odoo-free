{
    "name": "Sales Commission (Lite)",
    "summary": "A flat commission per salesperson, with per-category overrides, computed when customer invoices are posted, on Odoo 19 Community",
    "description": """
Sales Commission (Lite)
=======================

Pay each salesperson a percentage of what they invoice. Set a default
commission rate on the user, override it for particular product categories,
and the module writes one commission line per invoice line the moment a
customer invoice is posted.

What it does
------------
* **A default rate per salesperson** on the user form, and a **rate table**
  (salesperson, product category, percentage) that overrides it. The nearest
  matching category wins, so a rate on a parent category covers its children.
  A branch also uses its parent company's rates.
* **Commission lines on posting.** When a customer invoice is posted, one line
  per product line: salesperson, customer, date, product, category, base
  (the line's untaxed amount in company currency, as booked), rate and amount.
* **Credit notes take back what was earned.** A posted credit note writes
  negative lines. One made from an invoice takes back at the rate that
  invoice earned, from the salesperson who earned it, and nothing where the
  invoice earned nothing.
* **Reset or cancel withdraws.** Resetting an invoice to draft, or cancelling
  it, removes its unpaid commission lines; posting it again recomputes them
  once. There is never a duplicate. Changing the salesperson of a posted
  invoice moves its commission.
* **Report.** Commission lines in list, pivot and graph views, grouped by
  salesperson and month, with a paid/unpaid filter.
* **Mark as paid.** Select the lines settled with the salesperson and stamp
  them with a paid date. Paid lines are history and never change: if their
  invoice is later reset, cancelled or re-assigned, the paid amount is taken
  back with negative unpaid lines, and accounting is never blocked.
* **Security.** Salespeople see their own commission lines and rates; sales
  and accounting managers see everyone's and can mark lines paid. Nobody edits
  a line by hand.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "author": "drkds",
    "website": "https://drkdsinfo.com",
    "support": "jyotinboghani@gmail.com",
    "license": "LGPL-3",
    "depends": ["sale", "account"],
    "data": [
        "security/drkds_commission_security.xml",
        "security/ir.model.access.csv",
        "views/drkds_commission_rate_views.xml",
        "views/drkds_commission_line_views.xml",
        "views/res_users_views.xml",
        "views/account_move_views.xml",
        "views/menus.xml",
    ],
    "images": [],
    "installable": True,
    "application": False,
    "auto_install": False,
}
