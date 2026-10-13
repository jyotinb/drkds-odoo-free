# Changelog

## 19.0.1.0.0 - 2026-10-13

First release.

- Statement of account wizard on contacts (single or multiple): date range,
  Activity or Outstanding only, optional vendor side.
- QWeb PDF per partner: opening balance, lines with date, document,
  reference, due date, debit, credit and running balance, closing balance,
  ageing buckets 0-30, 31-60, 61-90 and over 90 days as at the end date.
- Foreign-currency items shown in company currency with the original amount
  noted on the line.
- Send by Email: PDF attached to the contact's chatter and emailed with an
  editable mail template.
- Statement smart button and non-stored ageing fields on the partner form.
- Company bank account and footer note settings under Invoicing.

### Fixed during review, before release

- Print from the wizard produced a blank PDF in the browser: the web client
  requests a report that carries data without record ids, so the report now
  takes its partners from the data.
- Send by Email failed with an access error for Billing users without
  Contact Creation (the Odoo 19 default) and was offered to Accounting
  read-only users. Send is now for Invoicing users only; the chatter post is
  made on their behalf, and they remain its author.
- The statement was emailed to every follower of the contact (for example
  the salesperson). It is now logged as a note and mailed only to the
  selected contacts. The mail template no longer uses default recipients.
- Selecting a person at a company emailed the company's address, or refused
  to send when the company had none. The email now goes to the contacts
  selected.
- Send ran wkhtmltopdf once per partner (about 2.6 s each). Statements are
  now rendered together and split per partner.
- A PDF run of a few hundred statements crashed wkhtmltopdf (error -11).
  Large runs are now rendered 50 statements at a time and merged.
- Invoices posted in a branch were missing from the parent company's
  statement and ageing. The company's branches are now included.
- On an Outstanding only statement, a part-paid foreign-currency invoice
  showed its full original amount. It now shows the amount still open in
  that currency, and exchange-difference lines no longer show a zero foreign
  amount.
- A statement for a second company was emailed with the sender's main
  company in the subject.
- The ageing fields on the partner had no access groups: a plain employee
  reading them got an access error, and a salesman got figures limited to his
  own invoices. They are now limited to Billing and Accounting read-only
  users, as core does for the partner's credit.
- Dates printed in ISO format (2024-06-30) instead of the language's format.
- A bank account deleted from the company (archived by Odoo 19) was still
  printed under "Please remit to".
- The bank line printed a stray space before the comma.
- The test named for another company never posted in one; it now does.
