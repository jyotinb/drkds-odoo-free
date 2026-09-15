# GST Outward and Inward Summary (India)

A period GST summary by rate, by state and by HSN, for checking before you file.

Pick a period and a company, press Compute, and read three tables back. It is
the working paper you want open next to the return before you press submit.

## Why this exists

Odoo 19 Community ships the Indian localisation's GST plumbing — the tax tags,
the place of supply, the HSN field and the GSTR section tag on invoice lines —
but no report that adds them up for a period. This module is that report.

## What you get

| View | Contents |
|---|---|
| Outward supplies | Taxable value, CGST, SGST, IGST and cess by combined GST rate and place of supply, with the GSTR section Odoo assigned |
| Inward supplies | The same breakdown for vendor bills and debit notes |
| HSN summary | HSN/SAC, description, UQC, quantity, taxable value and tax per rate |
| Reconciliation | Period totals grouped the way GSTR-3B table 3.1(a) and the GSTR-1 registered/unregistered split present them |

Every row has a drill-down button that opens the documents behind the figure.

## Where the numbers come from

Nothing here matches on tax names. A tax lands in the CGST, SGST, IGST or cess
column because of the repartition tax tag it carries, read through the Indian
localisation's own `account.tax.l10n_in_gst_tax_type`. Place of supply is the
localisation's place-of-supply field on the document, HSN/SAC is the field on
the invoice line, and the UQC is the GST unit code on the unit of measure. The
B2B/B2C split is the localisation's own `l10n_in_gstr_section` tag, not a guess
at the recipient's registration status.

Amounts come from Odoo's own tax engine, the same code path that produces the
invoice totals, so the summary and the invoice cannot disagree about rounding.

Credit notes and debit notes are subtracted from the period rather than listed
separately, because that is how they affect the supplies of a period.

## What this is not

This is a **check-before-you-file summary**. It does not generate a GST return,
it does not produce a filing-ready JSON, and it never contacts a government
portal. Compare its figures against the return your filing tool prepares and
investigate any difference before you file.

Input tax credit is shown as a single inward figure and is **not** split into
eligible and ineligible. Odoo 19 Community records no ITC eligibility flag on a
tax or an account, so any such split would be invented rather than read, and an
invented ITC figure is worse than none.

## Export

XLSX when the standard `xlsxwriter` library is present in the Odoo environment,
CSV otherwise. No extra Python package is ever required.

## Installation

Copy the module into your addons path, update the apps list and install
**GST Outward and Inward Summary (India)**. It depends on `l10n_in`, the
Community Indian localisation (LGPL-3), which is where the GST tax tags, place
of supply and HSN fields live.

Open it at **Accounting > Reporting > GST Summary (India)**.

This module is a tool to assist with compliance workflows. Responsibility for
statutory compliance rests with the user and their tax professional.

The drkds India accounting app adds GSTR-1 and GSTR-3B preparation and GSTR-2A
reconciliation.

Part of the drkds Indian SME suite for Odoo 19 Community.
