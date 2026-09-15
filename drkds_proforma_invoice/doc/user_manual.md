# Proforma Invoice — user manual

## What a proforma invoice is

A proforma invoice is a commercial offer laid out like an invoice. A buyer uses
it to open a letter of credit, to clear goods through customs, to release an
internal budget or to obtain an import licence. It is **not** a tax invoice:

- it recognises no revenue and no receivable,
- it creates no tax liability,
- it gives the buyer no input tax credit,
- and it must not carry an invoice number.

## Installing

Install **Proforma Invoice** (`drkds_proforma_invoice`). It depends only on
Sales and works on Odoo 19 Community.

## Creating a proforma

### From a quotation

Open the quotation and press **Create Proforma** in the header. The new
document copies:

- the invoicing contact,
- every order line including sections and notes,
- quantities, units, unit prices and discounts,
- the taxes on each line,
- the order currency and the validity date,
- the payment term wording, into **Terms**.

### From a draft customer invoice

Open the draft invoice and press **Create Proforma**. The invoice stays draft
and unnumbered — pressing the button does not post it and does not allocate an
invoice number.

Posted invoices refuse the button: once a real invoice exists, a proforma has
no purpose.

## Working with the document

| Field | Meaning |
| --- | --- |
| Proforma Number | Drawn from the `PRO/` sequence. Never from an invoice journal. |
| Proforma Date | Date shown on the PDF. |
| Valid Until | Date after which the quoted prices are no longer held. |
| Customer | Party the proforma is addressed to. |
| Currency | The source document's currency. Nothing is converted. |
| Lines | A snapshot of the source. Editing the quotation later does not rewrite it. |
| Taxes | Computed for information. No tax is recognised. |
| Terms | Payment and delivery terms, printed under the totals. |
| Note | Free text printed at the foot of the document. |
| Disclaimer | The "not a tax invoice" statement. Defaults to the company setting. |

## Statuses

- **Draft** — being prepared. Not visible on the portal.
- **Issued** — handed to the customer. Visible on the portal, printable,
  emailable.
- **Cancelled** — withdrawn. A cancelled proforma is never auto-converted.
- **Converted** — the source document has been invoiced for real. The proforma
  links to that invoice and can no longer be cancelled or deleted.

Conversion happens automatically: invoicing a quotation, or posting the source
draft invoice, marks every open proforma behind it converted.

## Printing and sending

**Print** produces the PDF. **Send by Email** opens the composer with the
proforma mail template loaded and the PDF attached.

## Portal

A customer who can already open the quotation on the portal sees a **Proforma
Invoices** block on that page listing every issued proforma, with a link to
view it and a button to download the PDF. Access is decided entirely by the
sale order's own portal rules — this module adds no new way in. A proforma
drawn from a draft invoice, with no sale order behind it, is not reachable from
the portal.

## Configuring the disclaimer

**Sales > Configuration > Settings > Quotations & Orders > Proforma
Disclaimer**. The default reads:

> This document is a proforma invoice. It is not a tax invoice, it creates no
> accounting entry and no tax liability, and it confers no right to input tax
> credit or to any tax deduction. A tax invoice will be issued separately once
> the supply is made.

Each proforma keeps its own copy, so changing the setting does not rewrite
documents already sent.

## Why no accounting entry can happen

The proforma is a model of its own. It does not inherit `account.move`, it
holds no journal, no account and no accounting line, and its only relations to
accounting are the two read-only links to the source draft invoice and to the
invoice that eventually replaced it. There is therefore no field to fill and no
method to call that could produce a journal entry. Calling `action_post` on a
proforma raises an error rather than doing nothing silently. The test suite
asserts all of this, and asserts that the invoice sequence does not skip a
number when a proforma is issued between two real invoices.

## Licence

LGPL-3. Part of the drkds Indian SME suite for Odoo 19 Community.
