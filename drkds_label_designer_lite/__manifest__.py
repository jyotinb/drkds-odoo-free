{
    "name": "Label Designer Lite",
    "summary": "Print product, lot, package and transfer labels at a custom physical size, "
               "with your own choice of fields and a barcode",
    "description": """
Label Designer Lite
===================

Odoo's own label wizard prints five fixed sheet layouts - Dymo, 2x7, 4x7 and
4x12 with or without price - on an A4 sheet, with a fixed set of fields. If your
stock is a 50 x 25 mm thermal roll, or the label has to carry a lot number, an
expiry date or a field of your own, there is no way through it.

This module adds label templates that state their own size.

It does not replace the built-in wizard, and it is not meant to. If you print
labels on A4 sheets in one of those grids, Odoo's own wizard already does the
job and there is no reason to install anything. This module is for label stock
that has its own size, or for contents core's fixed templates do not carry.

What it does
------------
* **A real physical page.** Each label template generates its own
  ``report.paperformat`` with the width and height you typed, in millimetres.
  A 50 x 25 mm label is a 50 x 25 mm page, not a small rectangle in the corner
  of an A4 sheet. Smart shrinking is disabled so the printer driver cannot
  rescale it.
* **Your own fields.** A label is a list of lines. A line prints a field read by
  dotted path from the record - ``default_code``, ``barcode``,
  ``expiration_date``, ``product_id.name``, or any field another module or
  Studio added - plus fixed text, the company logo, or a barcode. Field paths
  are checked against the model when you save, so a typo is refused at
  configuration time rather than at the printer.
* **Barcodes** through Odoo's existing barcode engine: automatic, Code 128,
  EAN-13, EAN-8 or QR. No extra library and no pip install.
* **Four record types**: products, lot and serial numbers, packages and
  transfers. Printing starts from the Actions menu of the record, with a
  number of copies.
* **Per line formatting**: font size in points, bold, alignment, and an empty
  value can drop its line so the rest of the label closes up.

What it deliberately does not do
--------------------------------
The layout is a declarative list of lines, not a drag and drop canvas. That
keeps the module small enough to trust and covers the roll formats most
warehouses actually print.

The drkds Label Designer app adds a drag and drop visual designer, customer
specific label variants and printing from any document.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Inventory/Inventory",
    "author": "drkds",
    "website": "https://github.com/drkds/drkds-odoo-free",
    "license": "LGPL-3",
    "depends": ["stock"],
    "data": [
        "security/ir.model.access.csv",
        "report/drkds_label_templates.xml",
        "report/drkds_label_reports.xml",
        "views/drkds_label_template_views.xml",
        "wizard/drkds_label_print_views.xml",
        "views/drkds_label_menus.xml",
        "data/drkds_label_template_data.xml",
    ],
    "images": ["static/description/cover.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
