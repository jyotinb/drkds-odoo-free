# Label Designer Lite

Print product, lot, package and transfer labels **at the physical size of your
label stock**, with the fields you choose and a barcode.

## Why

Odoo 19 Community already ships a label wizard (`product.label.layout`). It
offers five fixed choices - Dymo, 2 x 7, 4 x 7 and 4 x 12 with or without price
- laid out on an A4 sheet, with a fixed set of fields: name, internal reference,
price, barcode and a free HTML block. Stock's extension adds four fixed ZPL
sizes for Zebra printers.

None of that reaches a 50 x 25 mm thermal roll, a lot number, an expiry date or
a field of your own. This module does.

It does not replace the built-in wizard, and it is not meant to. If you print
labels on A4 sheets in one of those grids, Odoo's own wizard already does the
job and there is no reason to install anything. This module is for label stock
that has its own size, or for contents core's fixed templates do not carry.

## What it does

- **A real physical page.** Each label template generates its own
  `report.paperformat` at the width and height you typed, in millimetres, with
  smart shrinking disabled. A 50 x 25 mm label comes out 50 x 25 mm.
- **Your own fields.** A label is an ordered list of lines. A line prints a
  field read by dotted path from the record (`default_code`, `barcode`,
  `expiration_date`, `product_id.name`, or a field added by another module or
  Studio), fixed text, the company logo, or a barcode. Paths are validated
  against the model on save.
- **Barcodes** through Odoo's own barcode engine - automatic, Code 128, EAN-13,
  EAN-8, QR. No extra library, no pip dependency.
- **Four record types**: product, lot/serial, package, transfer. Print from the
  record's Actions menu with a number of copies.
- **Per line formatting**: font size in points, bold, alignment, and an option
  to drop a line whose value is empty.

## What it does not do

The layout is a declarative list, not a drag and drop canvas. That is a
deliberate limit, not an oversight.

## Install

Copy into your addons path, update the apps list, install **Label Designer
Lite**. It depends on `stock` only.

Two ready templates are installed: *Product 50 x 25 mm* and *Lot 50 x 25 mm*.
Find them under **Inventory > Configuration > Label Templates**.

## Printing

Select one or more products (or lots, packages, transfers), open **Actions >
Print Labels (drkds)**, choose a template and the number of copies.

The drkds Label Designer app adds a drag and drop visual designer, customer
specific label variants and printing from any document.

Part of the drkds Indian SME suite for Odoo 19 Community.
