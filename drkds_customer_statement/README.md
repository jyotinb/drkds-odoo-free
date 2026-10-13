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
- **Company currency throughout.** A foreign-currency item is listed at the
  company-currency value of its journal item, with its amount in the original
  currency noted next to the reference. On an *Outstanding only* statement
  that note is the amount still open in that currency. Lines with no foreign
  amount, such as exchange differences, carry no note.
- **Send by Email.** Renders the statements together (50 per PDF run, not one
  run per partner), emails each statement to the contacts you selected with
  the *Statement of Account: Send* mail template, and logs it as a note with
  the PDF attached on the company's chatter. Only the selected contacts
  receive it; followers of the contact are not mailed.
- **Partner form.** A **Statement** smart button, and four ageing fields plus
  the total due on the Invoicing tab (computed when read, never stored),
  visible to Billing and Accounting read-only users.
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
3. **Print** for one PDF with every statement, or **Send by Email** to email
   each statement and log it on the company's chatter.

Statements cover the commercial entity: a contact person's invoices roll up
to their company's statement. The email goes to the contacts you selected:
select the company to email the company's address, or a person at the
company (for example the accounts contact) to email that person the
company's statement. Every selected contact needs an email address.

Access: Billing and Accounting read-only users can open the wizard and
print; **Send by Email** needs the Invoicing (Billing) right. Contact
Creation is not needed.

## Notes

- Only posted receivable (and, when asked, payable) journal items of the
  chosen company and its branches are read. A branch is part of the same
  legal entity, so the parent's statement includes it; a branch's own
  statement shows only its postings. Draft documents never appear.
- Ageing days are counted from the due date, or the document date when there
  is none.
- The partner ageing fields reflect today's receivable position in the
  current company and its branches, and are recomputed on every read.
- Dates on the statement follow the language's date format.
- A bank account removed from the company (Odoo archives it) is no longer
  printed, even while the setting still points at it.
- Large selections are rendered 50 statements per PDF run and merged into
  one document. Allow about 15 seconds per 50 statements: a run of several
  hundred needs the server's `limit_time_real` above Odoo's 120-second
  default.
- No follow-up levels, no automatic reminders, no scheduled jobs.

## Tests

`tests/test_statement.py` checks the running balance, as-at ageing, the
multi-currency rows (including the open foreign amount after a part payment
and an exchange difference), the vendor side, contact roll-up, other
companies and branches, field access and the rendered HTML, with
hand-computed figures for five invoices and two payments at fixed dates.
`tests/test_send.py` covers who may send, who receives the email and the
single rendering run. `tests/test_print_http.py` prints through
`/report/download` exactly as the web client does. `tests/test_pdf_batches.py`
checks that large runs are rendered in batches. `tests/test_scenario.py` runs
month-end statements for two customers through the wizard, including print
and send.

## Dependencies

`account` only. Odoo 19 Community.

## Licence

LGPL-3.

The drkds Accounting Pro app adds payment follow-up levels, automated reminders and collection dashboards.

Part of the drkds Indian SME suite for Odoo 19 Community.
