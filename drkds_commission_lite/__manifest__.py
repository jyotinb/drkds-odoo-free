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
* **Commission lines on posting.** When a customer invoice is posted, one line
  per product line: salesperson, customer, date, product, category, base
  (the line's untaxed amount in company currency), rate and amount.
* **Credit notes count against.** A posted credit note writes negative lines,
  so a refund takes back the commission it reverses.
* **Reset or cancel removes.** Resetting an invoice to draft, or cancelling
  it, removes its unpaid commission lines; posting it again recomputes them
  once. There is never a duplicate.
* **Report.** Commission lines in list, pivot and graph views, grouped by
  salesperson and month, with a paid/unpaid filter.
* **Mark as paid.** Select the lines settled with the salesperson and stamp
  them with a paid date. Paid lines are protected: an invoice whose commission
  was paid cannot be reset to draft until a manager marks it unpaid.
* **Security.** Salespeople see their own commission lines; sales and
  accounting managers see everyone's and can mark lines paid.

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
