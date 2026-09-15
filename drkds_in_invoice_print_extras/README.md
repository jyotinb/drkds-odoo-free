# Indian Invoice Print Extras

**Odoo's own Indian localisation already produces the GST invoice.** With
`l10n_in` installed, the standard invoice PDF is titled *Tax Invoice*, *Bill of
Supply* or *Invoice-cum-Bill of Supply* as the case requires, carries the
HSN/SAC column, prints the full HSN summary with the CGST/SGST, IGST and Cess
split, and shows the place of supply and the GSTINs. None of that is this
module's work and this module does not repeat it.

This module fills the small gaps that are left. It adds five blocks to that
same PDF and changes nothing else.

## What it adds

- **GST state codes.** The two digit code lives on the state record as
  `l10n_in_tin` and the localisation maintains it, but never prints it. It now
  appears beside the supplier state, the buyer state, the shipping state and
  the place of supply.
- **A proper bank block.** The standard PDF mentions the recipient bank only as
  a phrase inside the payment terms sentence. You get a labelled block with
  account holder, account number, **IFSC** and **branch**. With no recipient
  bank on the invoice, the company's own first bank account is used.
- **A declaration.** The customary declaration sentence, as a company setting
  with a sensible default. Not in the standard PDF at all.
- **A signature block.** *For \<company\>* and *Authorised Signatory*. Not in
  the standard PDF at all.
- **A reverse charge marker.** `l10n_in` already flags reverse charge on the tax
  and shows it on the tax form, but never prints it on the invoice.

## What it does not do

No second report, no extra print menu entry, no new PDF — there is one invoice
PDF and this module extends it. It touches no amount, no tax computation and no
total, and it does not change how amounts are spelled in words.

## Scope, honestly

This is a print-layout module. It makes the standard Indian invoice PDF more
complete for everyday use; it is not a GST compliance engine and does not claim
to be one.

## Configuration

Accounting → Configuration → Settings → Customer Invoices → **Invoice
Declaration**. A sensible default is installed.

The bank account's **IFSC** is the BIC field of the bank record (Contacts →
Configuration → Banks) and the **branch** is the bank name.

## Install

Copy into your addons path and install `drkds_in_invoice_print_extras`. It
depends only on `l10n_in`, the LGPL Indian localisation shipped with Odoo
Community.

## Tests

```
odoo-bin -d <db> -i drkds_in_invoice_print_extras --test-enable --stop-after-init
```

---

This module is a tool to assist with compliance workflows. Responsibility for
statutory compliance rests with the user and their tax professional.

The drkds Accounting India app adds GSTR-1 and GSTR-3B preparation, GSTR-2A reconciliation, TDS and TCS with Form 26Q and an E-Way Bill register.

Part of the drkds Indian SME suite for Odoo 19 Community.
