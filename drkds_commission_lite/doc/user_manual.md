# Sales Commission (Lite) — user manual

## 1. Who can do what

| Role | Group | Can |
|---|---|---|
| Salesperson | Sales > User: Own Documents Only | See their own commission lines and rates under Sales > Commissions |
| Sales manager | Sales > Administrator | Set rates, see everyone's lines, mark lines paid or unpaid |
| Accounting manager | Accounting > Administrator | Same as the sales manager |
| Billing | Accounting > Billing | Read commission lines (for instance from the invoice's smart button), not the rates |

Nobody edits a commission line by hand: lines are written by the invoices, and
managers only mark them paid or unpaid. A salesperson's rates are visible to
the managers and to that salesperson, not to colleagues.

With several companies, rates and lines belong to one company and are only
seen from that company. A branch also uses the rates of its parent company
(see section 2).

## 2. Set the rates

### Default rate per salesperson

Settings > Users > open the salesperson > **Commission** tab > *Default
Commission (%)*. This applies to every product unless a category rate
overrides it. Leave it at 0 for a salesperson who earns no commission.

### Category rates

On the same tab, add a row per product category: category and percentage.
Or use **Sales > Configuration > Commission Rates**, which lists every
salesperson's category rates and lets you add them in bulk.

Rules:

- A category rate applies to products in that category and in all of its
  sub-categories, unless a sub-category has its own rate. The nearest one
  wins.
- A category rate of 0 switches commission off for that category.
- One rate per salesperson, category and company. A percentage must be
  between 0 and 100.
- A branch uses its own rates and its parent company's. For the same
  category the branch's own rate wins, so a rate set once on the parent
  company covers every branch until a branch needs a different one.

## 3. How commission lines appear

Post a customer invoice with a salesperson on it (the *Salesperson* field in
Other Info, filled from the sales order or defaulting to the person who
created the invoice). On posting, one commission line is written per product
line:

| Field | Meaning |
|---|---|
| Salesperson | The invoice's salesperson |
| Invoice / Invoice Line | Where the line comes from |
| Customer | The invoice's commercial partner |
| Invoice Date | The invoice date; the month used in the report |
| Product, Product Category | From the invoice line |
| Base | The line's untaxed amount after discount, in company currency as booked on the invoice |
| Rate (%) | The rate chosen as in section 2 |
| Commission | Base x Rate / 100 |
| Status | Unpaid or Paid |
| Paid On | Date the line was marked paid |

The invoice shows a **Commission** smart button with the number of lines.

A **credit note** posts negative lines. When it was made from an invoice
(the invoice's *Credit Note* button), it takes back exactly what that invoice
earned: the same rate, from the same salesperson, and nothing on products that
earned no commission there. Changing a rate after the invoice, or giving the
salesperson a rate they did not have then, does not change what a credit note
takes back. If the customer returns part of an order, the credit note takes
back only the commission on the returned part. A credit note entered on its
own, without an invoice behind it, uses the rates in force when it is posted.

**Resetting an invoice to draft, or cancelling it,** removes its unpaid
commission lines. Posting again writes them afresh with the rates in force at
that moment. Posting twice never duplicates.

**Changing the salesperson** on a posted invoice (Other Info tab) moves its
commission to the new salesperson.

Invoices posted before the module was installed have no lines, and a credit
note made from one takes nothing back. Reset and re-post them if their
commission is needed.

## 4. The report

**Sales > Commissions** opens the lines grouped by salesperson and month, with
totals for base and commission.

- **Pivot** gives the salesperson-by-month matrix. Add *Product Category* or
  *Customer* as a row for a finer breakdown.
- **Graph** stacks monthly commission by salesperson.
- Filters: *Unpaid*, *Paid*, *Invoices*, *Credit Notes*, and an *Invoice
  Date* period filter.

A salesperson opening this menu sees only their own lines.

## 5. Paying out

When a period is settled with the salesperson:

1. Sales > Commissions, filter **Unpaid**, group or filter by the period.
2. Select the lines and choose **Mark as Paid** in the list header (or press
   the button on a single line).
3. The lines turn *Paid* with today's date as *Paid On*.

Only sales and accounting managers can mark lines paid.

**Paid lines are history.** A paid line is never changed or deleted, and
accounting is never blocked by it: an invoice whose commission was paid can
still be reset to draft or cancelled. When that happens, the paid amount is
taken back with a negative unpaid line on the same invoice, so the
salesperson's unpaid total shows what they owe. If the invoice is posted
again, only the difference from what was paid is written (for example 30 more
if 50 was paid and the invoice now earns 80). The same happens when the
salesperson of a paid invoice is changed. Settle these lines like any other:
select them with the rest of the period and **Mark as Paid**.

An invoice that carries paid commission cannot be deleted. Cancel it instead,
so the record of the payment stays.

Use **Mark as Unpaid** only to undo a mistaken click: a line marked unpaid is
an ordinary unpaid line again, and the next reset of its invoice removes it.

## 6. Questions

**An invoice posted but no line appeared.** Check that the invoice has a
salesperson, that the salesperson has a non-zero rate for the product's
category or a non-zero default, and that the document is a customer invoice
or credit note (not a vendor bill or receipt).

**The amount looks wrong on a foreign-currency invoice.** The base is the
amount booked in company currency, at the currency rate shown on the invoice
(set from the rate table at the invoice date, or typed in). A credit note made
from an invoice keeps that invoice's rate, so it takes back exactly what was
earned even if the table has moved since.

**I changed a rate; old invoices did not change.** Rates are read at posting
time. Lines already written are not touched. Reset and re-post an invoice to
recompute it; if its commission was already paid, only the difference is
written.

**A negative unpaid line appeared on an invoice, not a credit note.** The
invoice was reset, cancelled or given another salesperson after its
commission had been paid. The negative line takes the paid amount back.
