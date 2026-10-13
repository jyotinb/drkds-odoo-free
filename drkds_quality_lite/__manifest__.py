{
    "name": "Quality Checks on Transfers (Lite)",
    "summary": "Pass/fail and measured quality checks on receipts and deliveries, on Odoo 19 Community",
    "description": """
Quality Checks on Transfers (Lite)
==================================

Odoo 19 Community receives and ships goods, but it has no place to record
whether the goods were actually inspected before they went on the shelf or
out of the door. This module adds that one record and the rule that goes
with it.

What it does
------------
* **Control points** - say what must be checked (a product or a whole
  product category), on which operation types, with written instructions
  the inspector reads on the spot.
* **Two kinds of check** - a plain pass/fail decision, or a measured value
  with a minimum, a maximum and a unit. A measure outside the range fails on
  its own; nobody has to remember the tolerance.
* **Checks raised automatically** - when a transfer is confirmed, one check
  is created for every move that matches a point, whoever confirms it.
  Nothing is raised twice, and a check follows its move into a backorder or
  a split-off transfer.
* **A gate on validation** - a transfer cannot be validated while a blocking
  check on the goods being validated is still to do or has failed. Goods
  that did not arrive go to the backorder with their checks. A point can be
  marked non-blocking so it records the result without holding up the goods.
* **Numbered, traceable records** - each check is numbered QC/00001 onward,
  linked to its transfer, move, product and lot, and carries who decided,
  when, a note and any photo attached through the chatter.
* **Smart button on the transfer** - the inspector opens the checks from
  the transfer itself; the count shows how many are still open.

Deliberately not included
-------------------------
No checks on manufacturing orders, no sampling plans, no worksheets, no
quality alerts workflow. The lite module records inspections on transfers
and keeps bad goods from being validated, nothing more.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Inventory/Inventory",
    "author": "drkds",
    "website": "https://drkdsinfo.com",
    "support": "jyotinboghani@gmail.com",
    "license": "LGPL-3",
    "depends": ["stock"],
    "data": [
        "security/drkds_quality_security.xml",
        "security/ir.model.access.csv",
        "data/drkds_quality_data.xml",
        "views/drkds_quality_point_views.xml",
        "views/drkds_quality_check_views.xml",
        "views/stock_picking_views.xml",
        "views/drkds_quality_menus.xml",
    ],
    "images": [],
    "installable": True,
    "application": True,
    "auto_install": False,
}
