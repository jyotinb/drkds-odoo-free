# Label Designer Lite - user manual

## 1. What this module is for

Your label stock has a size. A roll of 50 x 25 mm thermal labels, a 100 x 150 mm
shipping label, a 38 x 21 mm jewellery tag. Odoo's built-in label wizard prints
fixed grids on an A4 sheet plus one fixed Dymo size, and always the same fields.
This module lets you declare the size and the contents yourself.

## 2. Creating a label template

**Inventory > Configuration > Label Templates > New**

| Field | Meaning |
| --- | --- |
| Name | Your name for the label, e.g. "Shelf label 50 x 25". |
| Applies To | Product, Lot / Serial Number, Package or Transfer. This decides which fields are available and where the label can be printed from. |
| Size (mm) | Width and height of one label. Both must be greater than zero. |
| Margins (mm) | White space kept inside the label. They are applied inside the page, not as printer margins, so nothing is lost. |
| Print Outline | Draws a thin rectangle round the label. Switch it on while calibrating the printer, off for production. |
| Paper Format | Generated for you. Read only. It is rewritten whenever you change the size. |

## 3. The layout

The **Layout** tab is an ordered list. Lines print top to bottom. Drag the
handle to reorder.

Each line has a **Content**:

- **Field Value** - reads a field from the record being printed. Type the
  technical name in **Field Path**. Dotted paths follow relations, for example
  `product_id.default_code` on a lot label. If the field does not exist the
  record refuses to save, so you find out now and not at the printer.
- **Fixed Text** - the same words on every label, e.g. "Keep refrigerated".
- **Barcode** - a barcode of the value at the given field path. Choose the
  symbology (Automatic, Code 128, EAN-13, EAN-8, QR), the height in millimetres,
  and whether to print the value underneath.
- **Company Logo** - the logo of the record's company, at the given height.

Formatting per line: **Font Size (pt)**, **Bold**, **Align**, plus **Prefix**
and **Suffix** text around the value (for example a prefix of `Exp: `).

**Hide If Empty** drops the line when the record has no value for it, so the
rest of the label closes up rather than leaving a gap.

### Useful field paths

| Record type | Path | Prints |
| --- | --- | --- |
| Product | `display_name` | Product name with its variant values |
| Product | `default_code` | Internal reference |
| Product | `barcode` | Barcode value |
| Product | `list_price` | Sales price |
| Product | `uom_id` | Unit of measure |
| Lot / Serial | `name` | The lot or serial number |
| Lot / Serial | `product_id` | The product |
| Lot / Serial | `expiration_date` | Expiry, when *Expiration Dates* is enabled in Inventory settings |
| Package | `name` | Package reference |
| Transfer | `name` | Transfer reference |
| Transfer | `partner_id` | Delivery contact |

A maximum retail price, a batch code or any other value you keep in a custom
field works the same way: put its technical name in the field path.

## 4. Printing

Select one or more records in a list, or open one, then **Actions > Print
Labels (drkds)**. Choose the template and the number of **Copies**, then
**Print**. Every copy is a separate label; ten copies of two products is twenty
labels.

## 5. Getting the size right on the printer

The generated PDF pages are exactly the size you typed. In the print dialog
choose **Actual size** or a scale of 100%, never "Fit to page", and select the
roll size in the printer driver. If the outline is on and it prints inside the
label edges, the size is right.

## 6. Limits

- The layout is a list of stacked lines. There is no free positioning and no
  drag and drop canvas.
- One label design is not varied per customer.
- Printing starts from products, lots, packages and transfers.

The drkds Label Designer app adds a drag and drop visual designer, customer
specific label variants and printing from any document.

Part of the drkds Indian SME suite for Odoo 19 Community.
