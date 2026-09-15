# User manual — GST Outward and Inward Summary (India)

## Before you start

Three things have to be right in the database, because the summary reads them
rather than inventing them.

1. **Taxes** are the Indian localisation's GST taxes, or copies of them. What
   matters is the repartition tax tag (`tax_tag_cgst`, `tax_tag_sgst`,
   `tax_tag_igst`, `tax_tag_cess`), not the tax name. A home-made tax with no
   tag is counted in the taxable value but shows no tax split.
2. **Place of supply** is set on the document. Odoo computes it from the
   customer or vendor address; check it on documents where the delivery state
   differs from the billing state.
3. **HSN/SAC code** is filled on the product or overridden on the invoice line.
   Lines with no code are grouped into a single blank row so that the gap is
   visible rather than silently dropped.

## Running a summary

Go to **Accounting > Reporting > GST Summary (India)**.

| Field | What it does |
|---|---|
| From / To | The period, by accounting date, not invoice date |
| Company | Which company's books to read |
| Include draft documents | Off by default. Tick it only to preview what a draft batch would add; a return is filed from posted documents |

Press **Compute**. Four tabs appear.

### Outward supplies

One row per combined GST rate, place of supply and GSTR section. Intra-state
CGST 9% + SGST 9% appears as a single 18% row, which is how both GSTR-1 and
GSTR-3B present it.

### Inward supplies

The same shape for vendor bills and debit notes.

Input tax credit is **not** split into eligible and ineligible. Odoo 19
Community records no ITC eligibility flag on a tax or an account, so the
information is simply not in the database. Rather than guess, the module omits
the distinction. If you track blocked credit, do it in your own analysis on top
of the inward figures here.

### HSN summary

One row per HSN/SAC, UQC and rate, with quantity, taxable value and the tax
split. Check three things: no blank HSN row, quantities that match what you
shipped, and a rate per HSN that matches your rate master.

### Reconciliation

The period totals, grouped so they can be read against a prepared return:

- **Outward taxable value, CGST, SGST, IGST, cess** — compare against GSTR-3B
  table 3.1(a).
- **Outward B2B / B2C taxable value** — compare against the registered and
  unregistered tables of GSTR-1. The split comes from the GSTR section Odoo
  assigned to each invoice line, not from a guess.
- **Inward taxable value and taxes** — compare against the input tax credit
  claimed in GSTR-3B table 4, after your own eligibility adjustments.

## Drilling down

Every row in every table has a magnifying-glass button. It opens the list of
documents that produced that figure. This is the fastest way to answer "why is
there 18% IGST to Gujarat when Gujarat is our own state" — open the row and
look at the invoices.

## Export

**Export** produces an XLSX workbook with one sheet per table when the standard
`xlsxwriter` library is available in the Odoo environment, and a single CSV
otherwise. No Python package is installed by this module.

## Limits worth repeating

- This is a summary for checking before filing. It is **not** a GST return and
  it produces **no** filing-ready JSON.
- No government portal is ever contacted. Nothing leaves your database.
- Figures follow the accounting date. A back-dated invoice posted after you ran
  a summary changes that period; run it again before you file.
- Documents outside India (company or document country other than IN) are
  ignored.

This module is a tool to assist with compliance workflows. Responsibility for
statutory compliance rests with the user and their tax professional.
