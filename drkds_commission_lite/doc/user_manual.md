# Sales Commission (Lite) — user manual

## 1. Who can do what

| Role | Group | Can |
|---|---|---|
| Salesperson | Sales > User: Own Documents Only | See their own commission lines and rates under Sales > Commissions |
| Sales manager | Sales > Administrator | Set rates, see everyone's lines, mark lines paid or unpaid |
| Accounting manager | Accounting > Administrator | Same as the sales manager |
| Billing | Accounting > Billing | Read commission lines (for instance from the invoice's smart button) |

With several companies, rates and lines belong to one company and are only
seen from that company.

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
| Base | The line's untaxed amount after discount, in company currency |
| Rate (%) | The rate chosen as in section 2 |
| Commission | Base x Rate / 100 |
| Status | Unpaid or Paid |
| Paid On | Date the line was marked paid |

The invoice shows a **Commission** smart button with the number of lines.

A **credit note** posts negative lines using the same rules. If the customer
returns part of an order, the credit note takes back only the commission on
the returned part.

**Resetting an invoice to draft, or cancelling it,** removes its commission
lines. Posting again writes them afresh with the rates in force at that
moment. Posting twice never duplicates.

Invoices posted before the module was installed have no lines. Reset and
re-post them if their commission is needed.

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

**Paid lines are protected.** An invoice whose commission has been paid cannot
be reset to draft or cancelled, and its lines cannot be deleted, until a
manager uses **Mark as Unpaid**. This is deliberate: once money has gone out,
reversing the invoice should be a conscious act that also decides what to do
about the commission.

## 6. Questions

**An invoice posted but no line appeared.** Check that the invoice has a
salesperson, that the salesperson has a non-zero rate for the product's
category or a non-zero default, and that the document is a customer invoice
or credit note (not a vendor bill or receipt).

**The amount looks wrong on a foreign-currency invoice.** The base is
converted to company currency at the invoice date. The rate table in
Accounting > Configuration > Currencies decides the conversion.

**I changed a rate; old invoices did not change.** Rates are read at posting
time. Lines already written are not touched. Reset and re-post an invoice to
recompute it, provided its lines are not paid.
