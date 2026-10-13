# Sales Commission (Lite)

A flat commission per salesperson, computed when customer invoices are posted,
on Odoo 19 Community.

Give each salesperson a default percentage, override it for particular product
categories, and every posted customer invoice writes one commission line per
product line: who earned it, on what, the untaxed base, the rate and the
amount. Credit notes write negative lines. A report groups the lines by
salesperson and month, and a manager marks them paid when the money goes out.

## What you get

| Piece | What it does |
|---|---|
| Default rate | *Default Commission (%)* on the user form, Commission tab |
| Category rates | `drkds.commission.rate`: salesperson, product category, percentage, company. Sales > Configuration > Commission Rates, or the same tab on the user |
| Commission lines | `drkds.commission.line`: invoice, invoice line, salesperson, customer, invoice date, product, category, base, rate, amount, status (unpaid/paid), paid date |
| Report | Sales > Commissions: list with totals, pivot (salesperson x month) and graph; filters for paid, unpaid, invoices, credit notes, date; group by salesperson, month, status, customer, category |
| Mark as paid | Header action on the list and button on the form, for sales and accounting managers; *Mark as Unpaid* reverses it |
| Invoice link | A *Commission* smart button on the posted invoice |
| Security | Salespeople read their own lines and rates; sales managers and accounting managers see all lines, manage rates and settle lines; multi-company record rules |

## How the rate is chosen

For each product line of the invoice, the salesperson is the invoice's
*Salesperson* (`invoice_user_id`). The rate is:

1. the salesperson's rate on the product's category, if there is one;
2. else the rate on the nearest parent category that has one;
3. else the salesperson's *Default Commission (%)*.

A rate of zero at any of these levels means no commission for that line, and
no line is written. A rate on a parent category therefore covers all its
children unless a child has its own.

## Behaviour worth knowing

- **Posting, not payment, triggers the commission.** The line is written when
  the invoice is posted. The base is the invoice line's untaxed amount
  (`price_subtotal`, after discount) converted to company currency at the
  invoice date.
- **Credit notes count against.** A posted credit note (`out_refund`) writes
  negative lines with the same rules, so a refund takes back the commission on
  what it reverses. A partial credit note takes back only its own amount.
- **Reset to draft or cancel removes the lines.** Posting the invoice again
  recomputes them with the rates in force at that moment. There is never a
  duplicate: regenerating always replaces the unpaid lines of that invoice.
- **Paid lines are protected.** An invoice whose commission lines are marked
  paid cannot be reset to draft or cancelled, and the lines cannot be deleted,
  until a manager marks them unpaid. Regeneration leaves such an invoice
  alone.
- **Only customer invoices and credit notes.** Vendor bills, receipts and
  journal entries never produce commission. Section and note lines are
  skipped.
- **No salesperson, no commission.** An invoice without a salesperson writes
  nothing.

## Installation

Copy `drkds_commission_lite` into your addons path, update the apps list and
install **Sales Commission (Lite)**. Depends on `sale` and `account`.

## Configure and use

1. Settings > Users, open the salesperson, **Commission** tab: set *Default
   Commission (%)*, and add category rates in the table below if needed. The
   tab is visible to sales and accounting managers.
2. Or manage all category rates in one place: Sales > Configuration >
   Commission Rates.
3. Post customer invoices as usual, with the salesperson set on the invoice.
4. Sales > Commissions shows the lines grouped by salesperson and month.
   Switch to the pivot for the monthly matrix.
5. To settle a period: filter *Unpaid*, select the lines, **Mark as Paid**.

See `doc/user_manual.md` for the walkthrough.

## Not in this module

No commission on sales orders, payments or margins; no tiered or target-based
schemes; no payslip or vendor-bill generation for the commission; no team or
manager overrides. Invoices posted before the module was installed are not
back-filled: reset and re-post them if you need their commission.

The drkds Sales Pro app adds tiered schemes, team commissions and payout
documents.

Part of the drkds Indian SME suite for Odoo 19 Community.
