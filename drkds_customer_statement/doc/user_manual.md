# Customer and Vendor Statements — user manual

## What a statement of account is

A statement of account lists, for one partner and one period, every posted
document that affected what they owe you (or what you owe them), with a
running balance, and shows how old the open amounts are. Customers use it to
reconcile their ledger with yours; you use it at month end to prompt payment.

## Installing

Install **Customer and Vendor Statements** (`drkds_customer_statement`). It
depends only on Invoicing and works on Odoo 19 Community.

| Access right | Wizard, Print, smart button, ageing fields | Send by Email |
| --- | --- | --- |
| Invoicing: Billing (or above) | Yes | Yes |
| Accounting read-only | Yes | No (the button is hidden) |
| Anyone else (sales, purchase, employees) | No | No |

Sending does not need the *Contact Creation* right, which Odoo 19 does not
give new users by default.

## Settings

Invoicing > Configuration > Settings > Customer Invoices > **Statement of
Account**:

| Setting | Meaning |
| --- | --- |
| Statement Bank Account | One of the company's own bank accounts. Printed under "Please remit to". Leave empty to print nothing. Deleting the bank account in Odoo 19 archives it; an archived account is not printed. |
| Statement Footer Note | Free text printed at the foot of every statement. |

The email wording lives in Settings > Technical > Email Templates >
*Statement of Account: Send*.

## Running a statement

### From one contact

Open the contact and press the **Statement** smart button. The button shows
the partner's total due today.

### From several contacts

In Contacts, select the partners in the list, open **Actions** and choose
**Statement of Account**.

### The wizard

| Field | Meaning |
| --- | --- |
| From, To | The period. The end date is also the "as at" date for the ageing table. |
| Statement Type | **Activity**: every posted movement in the period, with the balance brought forward as the opening line. **Outstanding only**: only the items still open at the end date, each at the amount open then; no opening line. |
| Include Vendor Side | Also list vendor bills and vendor payments, so a partner who is both customer and supplier gets one net statement. |
| Company | The company whose statement it is (shown to multi-company users). The statement also includes the company's branches, which are part of the same legal entity. |
| Partners | The contacts selected. Contact persons roll up to their company's statement. |

**Print** produces one PDF with one statement per partner, each with its own
page numbers. Large selections are rendered 50 statements per run and merged;
allow about 15 seconds per 50 statements.

**Send by Email** renders all the statements together, then for each
company:

- emails its statement to the contacts you selected for it: select the
  company to use the company's address, or a person at the company, such as
  the accounts contact, to email that person the company's statement;
- logs the email as a note with the PDF attached on the company's chatter.

Only the selected contacts receive the email. Followers of the contact, such
as the salesperson, are not mailed the statement. The subject names the
company chosen in the wizard. A selected contact without an email address
stops the send before anything is posted, and the message names that
contact.

## Reading the statement

- **Opening balance**: the net of all posted items dated before the start
  date (Activity only).
- **Lines**: date, document number, reference (the document's reference or
  the item label), due date, debit, credit, running balance. Dates follow the
  language's date format. A line in a foreign currency shows its amount in
  that currency in brackets after the reference (on an *Outstanding only*
  statement, the amount still open in that currency); the debit, credit and
  balance are always in the company currency. Exchange-difference lines have
  no foreign amount and show no bracket.
- **Closing balance**: the running balance after the last line, with the
  column totals.
- **Ageing**: open amounts as at the end date, counted in days from the due
  date (or the document date if there is none): 0-30, 31-60, 61-90 and over
  90. Amounts not yet due are in the 0-30 column. The total equals the closing
  balance of an Activity statement when every reconciliation involves only
  the items listed.

Ageing is worked out as it stood on the end date: a payment reconciled after
that date does not reduce an earlier statement's open amounts.

## Partner form

On the Invoicing tab, **Receivable Ageing** shows the four buckets and the
total due for today, in the current company's currency, for the partner and
its contacts, in the current company and its branches. Only Billing and
Accounting read-only users see these fields. The figures are computed when the form is read and are not
stored, so they cannot be filtered or grouped on, but they are never stale.

## What it does not do

No follow-up levels, no automatic reminders, no scheduled jobs and no portal
page. It reads posted journal items and prints or sends them.
