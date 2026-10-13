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
| Mark as paid | Header action on the list and button on the form, for sales and accounting managers; *Mark as Unpaid* reverses it. Lines cannot be edited otherwise, by anyone |
| Invoice link | A *Commission* smart button on the posted invoice, for users who can read commission lines |
| Security | Salespeople read their own lines and rates; billing users read the lines (not the rates); sales managers and accounting managers see all lines, manage rates and settle lines; multi-company record rules |

## How the rate is chosen

For each product line of the invoice, the salesperson is the invoice's
*Salesperson* (`invoice_user_id`). The rate is:

1. the salesperson's rate on the product's category, if there is one;
2. else the rate on the nearest parent category that has one;
3. else the salesperson's *Default Commission (%)*.

A rate of zero at any of these levels means no commission for that line, and
no line is written. A rate on a parent category therefore covers all its
children unless a child has its own.

A branch (a company with a parent company) uses its own category rates and
those of its parent companies. For the same category, the branch's own rate
wins; a nearer category still beats a nearer company.

A credit note made from an invoice (the invoice's *Credit Note* button) does
not look rates up again: see below.

## Behaviour worth knowing

- **Posting, not payment, triggers the commission.** The line is written when
  the invoice is posted. The base is the invoice line's untaxed amount after
  discount, in company currency exactly as booked: a foreign-currency invoice
  uses its own currency rate (the one on the invoice, even if typed in by
  hand), not the rate table on another day.
- **Credit notes take back what was earned.** A posted credit note
  (`out_refund`) writes negative lines. When it was made from an invoice, it
  takes back at the rate that invoice earned, from the salesperson who earned
  it, and only on products that earned commission there: raising a rate
  afterwards, or giving a salesperson a rate they did not have, changes
  nothing. A partial credit note takes back only its own amount. A credit note
  entered on its own, with no invoice behind it, uses the rates in force.
- **Reset to draft or cancel withdraws the commission.** Unpaid lines are
  removed; posting the invoice again recomputes them with the rates in force
  at that moment. There is never a duplicate.
- **Paid lines are history.** A line marked paid is never changed or removed.
  Resetting or cancelling its invoice is still allowed: the paid amount is
  taken back with a negative unpaid line, so the salesperson's unpaid total
  shows what they owe. If the invoice is posted again, only the difference
  from what was paid is written. An invoice carrying paid commission cannot
  be deleted; cancel it instead.
- **A new salesperson moves the commission.** Changing the salesperson on a
  posted invoice moves its unpaid commission to the new salesperson; any
  commission already paid to the old one is taken back as above.
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
   Negative unpaid lines (commission taken back) are settled the same way and
   reduce the total.

See `doc/user_manual.md` for the walkthrough.

## Not in this module

No commission on sales orders, payments or margins; no tiered or target-based
schemes; no payslip or vendor-bill generation for the commission; no team or
manager overrides. Invoices posted before the module was installed are not
back-filled: reset and re-post them if you need their commission. Until then,
a credit note made from such an invoice takes nothing back either.

The drkds Sales Pro app adds tiered schemes, team commissions and payout
documents.

Part of the drkds Indian SME suite for Odoo 19 Community.
