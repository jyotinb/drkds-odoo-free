# Recurring Invoices (Lite) — user manual

## 1. Who can do what

- **Billing** (Accounting > Billing, group `account.group_account_invoice`):
  creates, starts, pauses and runs templates.
- **Read-only accounting** users can open templates and see their invoices;
  the action buttons are not shown to them.
- Users who read invoices without these rights (salespeople) do not see the
  *Recurring Template* field on invoices.
- With several companies, a template belongs to one company and is only seen
  from that company. A branch uses its parent company's sale journal and
  taxes, as its own invoices do.

## 2. Create a template

Go to **Accounting > Customers > Recurring Invoices** and click **New**.

| Field | Meaning |
|---|---|
| Name | What the contract is, e.g. *Office rent, Unit 4* |
| Customer | Invoiced party |
| Journal | Sale journal (a branch's is its parent company's); the generated invoices take their numbers from it |
| Currency | From the journal, else the company currency. Set it before adding lines |
| Payment Terms | From the customer, can be changed; copied onto each invoice. Empty: each invoice is due on its own date |
| Salesperson | Set on each invoice. The scheduler reads today's date in this person's time zone |
| Repeat Every | A number and a unit: day(s), week(s), month(s), year(s) |
| Next Invoice Date | Date of the next invoice to issue; the first one when starting |
| End Date | Last date an invoice may be issued for (inclusive). Empty means open-ended |
| Post Automatically | Post each invoice at once instead of leaving it in draft |
| Terms and Conditions | Printed on every generated invoice instead of the company's default terms. Empty: the company default is printed |

On the **Invoice Lines** tab add the lines. Picking a product fills the
description, the unit, the list price converted into the template's currency
(at the rate of the next invoice date), and the product's sale taxes.
Sections and notes are allowed and are copied to the invoice. The untaxed,
tax and total amounts at the bottom are what each invoice will carry before
the customer's fiscal position is applied (see section 4).

The reference (`REC/0001`) is allocated on save.

## 3. Start, pause, resume, finish

- **Start** moves the template to *Running*. It needs at least one real line
  and a next date on or before the end date. These two rules hold however a
  template is changed, also through an import or the API.
- **Pause** stops the scheduler for this template. The next date is kept.
- **Resume** continues from the kept next date. If that date is already in
  the past, the missed invoices are issued on the next run, one per date. If
  you do not want them, move the next date forward before resuming.
- **Mark as Done** closes the contract. Issued invoices are untouched.
- **Reset to Draft** reopens a finished template for editing. If its end
  date closed it, set a later end date before starting it again.

A template whose next date passes its end date marks itself *Done*.

## 4. What the scheduler does

The scheduled action *Recurring Invoices: generate due invoices* runs once a
day and serves every company, each invoice in its template's company, whatever
user the action is set to run as. "Today" is read in the time zone of the
template's salesperson: at 23:30 UTC it is already the next day for a
salesperson in India, and still the same day for one in New York. Without a
salesperson time zone the job's own (UTC) applies.

For each running template whose next date is today or earlier it:

1. looks for an existing, non-cancelled invoice of this template on that date
   and, if there is one, does not create another;
2. otherwise creates a customer invoice dated on the scheduled date with the
   template's lines, posting it when *Post Automatically* is set. The invoice
   gets its fiscal position as a typed invoice would (from the customer; with
   the Indian localisation, from the place of supply), and the template's
   taxes are mapped through it: GST becomes IGST for an inter-state customer,
   an export position gives its 0% or LUT tax. The payment terms, salesperson
   and terms and conditions come from the template; without payment terms the
   invoice is due on its own date;
3. moves the next date forward by one interval, and marks the template done
   if that takes it past the end date;
4. repeats while the next date is still not in the future, so a scheduler
   that was down catches up.

If a template fails (for instance the localisation refuses to post), the
reason is shown in a red box on the form and in the **Scheduler Error**
filter. The next date is not advanced, so the template is retried the
following day. Fix the cause, or press **Generate Now** to retry at once.

## 5. Generate Now

On a running or paused template, **Generate Now** issues the invoice for the
*Next Invoice Date* right away, opens it, and moves the next date forward. If
an invoice for that date already exists, the existing one is opened and the
date still moves on. Use it when the customer wants the invoice early, or to
retry after an error.

## 6. Dates at month end

The template remembers the day of month you set the next date on (shown
nowhere, but kept). From 31 January a monthly template goes to 28 February
(29 in a leap year) and back to 31 March. From 29 February 2024 a yearly
template goes to 28 February 2025, 2026 and 2027, then 29 February 2028.
Day and week intervals are plain additions. Editing the next date by hand
sets a new anchor day.

## 7. Finding things

| Filter | Shows |
|---|---|
| Draft / Running / Paused / Done | By status |
| Due Today or Earlier | Running templates the scheduler will pick up on its next run |
| Auto-posted | Templates that post their invoices |
| Scheduler Error | Templates whose last run failed |
| My Templates | Templates where you are the salesperson |
| Archived | Templates taken out of use |

Group by customer, status, interval unit or next-invoice month.

On an invoice, **Other Info** shows the **Recurring Template** it came from,
and the invoice search accepts the template name. The template's **Invoices**
smart button lists all of them.

## 8. Removing a template

A template that has issued invoices cannot be deleted; archive it (Action >
Archive) so the invoices keep their link. A template with no invoices can be
deleted.
