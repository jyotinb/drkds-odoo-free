# Proforma Invoice

Issue a numbered proforma invoice from a quotation or a draft invoice, without
touching your accounts.

A proforma invoice tells a buyer what a sale will cost, so they can open a
letter of credit, clear customs, release a budget or obtain an import licence.
It is not a tax invoice. It must create no accounting entry, no tax liability
and no receivable, and it must never consume an invoice number.

This module makes those guarantees structural rather than a matter of
discipline.

## Features

- **Create from a quotation or a draft customer invoice.** One button copies
  the customer, lines, quantities, unit prices, discounts, taxes and currency.
  The source document is only read, never written.
- **Its own sequence.** Numbers come from a dedicated `PRO/` sequence. Issuing
  a proforma cannot consume, reserve or skip an invoice number. This is the
  defect in almost every hand-rolled proforma.
- **No accounting entry, ever.** The proforma is not an `account.move`. It owns
  no journal, no account and no accounting line, and `action_post` on it raises
  an error instead of doing anything. Taxes are computed for display only.
- **A document nobody can mistake for an invoice.** The PDF is headed
  "Proforma Invoice" and carries a statement that it is not a tax invoice and
  confers no input tax credit. The wording is a company setting.
- **A visible trail.** Draft, issued, cancelled, converted. When the source
  document is invoiced for real, the proforma becomes converted and links to
  the resulting invoice.
- **Portal and email.** A customer who can see the quotation on the portal can
  view and download its proforma. A mail template attaches the PDF.

## Fields

Proforma number, date, validity date, customer, source document, currency,
lines copied from the source, taxes shown for information, untaxed, tax and
total amounts, terms and a free-text note.

## Usage

1. Open a quotation (or a draft customer invoice) and press **Create Proforma**.
2. Adjust the validity date, terms and note, then press **Issue**.
3. **Print** or **Send by Email**.
4. Invoice the source document as usual. The proforma turns **Converted** and
   points at the invoice.

Proforma invoices are also listed under **Sales > Invoicing > Proforma
Invoices**. The default disclaimer wording is in **Sales > Configuration >
Settings > Quotations & Orders**.

## Dependencies

`sale` only. Odoo 19 Community.

## Licence

LGPL-3.

The drkds suite for Odoo 19 adds deeper sales and compliance workflows,
including GSTR preparation and an e-invoice flow.

Part of the drkds Indian SME suite for Odoo 19 Community.
