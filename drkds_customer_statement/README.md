# Customer and Vendor Statements

Statement of account PDF per partner: opening balance, running balance,
ageing buckets, sent from the contact.

Odoo 19 Community shows a partner ledger on screen but has no printable or
mailable statement of account. This module adds one, driven from Contacts.

## Features

- **Wizard from Contacts.** Select one or many contacts, pick a date range,
  choose **Activity** (every posted movement in the period, with the balance
  brought forward) or **Outstanding only** (items still open at the end date,
  at the amount open then), and optionally **Include Vendor Side** so a
  partner who is both customer and supplier gets one net statement.
- **One PDF per partner.** Opening balance, one line per document with date,
  document number, reference, due date, debit, credit and running balance,
  closing balance, and ageing buckets 0-30, 31-60, 61-90 and over 90 days as
  at the end date. Items not yet due sit in the first bucket, so the buckets
  always add up to the total due.
- **Ageing as at the date.** Open amounts are replayed from the partial
  reconciliations dated on or before the end date, so a statement reprinted
  for an earlier month shows what the customer owed then.
- **Company currency throughout.** A foreign-currency invoice is listed at the
  company-currency value of its journal item, with the original currency
  amount noted next to the reference.
- **Send by Email.** Renders the PDF, posts it on the contact's chatter as a
  message with the PDF attached, and emails it with the *Statement of
  Account: Send* mail template, the same path as Send message on a chatter.
- **Partner form.** A **Statement** smart button, and four ageing fields plus
  the total due on the Invoicing tab (computed when read, never stored).
- **Settings.** The company bank account and a footer note printed on every
  statement, under Invoicing > Configuration > Settings > Customer Invoices.

## Install

Install **Customer and Vendor Statements** (`drkds_customer_statement`). It
depends only on Invoicing (`account`).

## Configure

1. Invoicing > Configuration > Settings > Customer Invoices > **Statement of
   Account**: choose the bank account to print and write the footer note.
2. Optionally edit the mail template under Settings > Technical > Email
   Templates > *Statement of Account: Send*.

## Use

1. Contacts: open a contact and press the **Statement** smart button, or
   select several contacts in the list and choose **Statement of Account**
   from the Actions menu.
2. Set **From**, **To**, the **Statement Type** and whether to include the
   vendor side.
3. **Print** for the PDF, or **Send by Email** to attach it to each contact's
   chatter and send it.

Statements are addressed to the commercial entity: a contact person's
invoices roll up to their company's statement.

## Notes

- Only posted receivable (and, when asked, payable) journal items of the
  current company are read. Draft documents never appear.
- Ageing days are counted from the due date, or the document date when there
  is none.
- The partner ageing fields reflect today's receivable position in the
  current company and are recomputed on every read.
- No follow-up levels, no automatic reminders, no scheduled jobs.

## Tests

`tests/test_statement.py` checks the running balance, as-at ageing, the
multi-currency row, the vendor side, contact roll-up and the rendered HTML
with hand-computed figures for five invoices and two payments at fixed dates.
`tests/test_scenario.py` runs month-end statements for two customers through
the wizard, including print and send.

## Dependencies

`account` only. Odoo 19 Community.

## Licence

LGPL-3.

The drkds Accounting Pro app adds payment follow-up levels, automated reminders and collection dashboards.

Part of the drkds Indian SME suite for Odoo 19 Community.
