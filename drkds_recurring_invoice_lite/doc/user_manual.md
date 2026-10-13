# Recurring Invoices (Lite) — user manual

## 1. Who can do what

- **Billing** (Accounting > Billing, group `account.group_account_invoice`):
  creates, starts, pauses and runs templates.
- **Read-only accounting** users can open templates and see their invoices.
- With several companies, a template belongs to one company and is only seen
  from that company.

## 2. Create a template

Go to **Accounting > Customers > Recurring Invoices** and click **New**.

| Field | Meaning |
|---|---|
| Name | What the contract is, e.g. *Office rent, Unit 4* |
| Customer | Invoiced party |
| Journal | Sale journal; the generated invoices take their numbers from it |
| Currency | From the journal, else the company currency |
| Payment Terms | Copied onto each invoice; empty means immediate payment |
| Salesperson | Set on each invoice |
| Repeat Every | A number and a unit: day(s), week(s), month(s), year(s) |
| Next Invoice Date | Date of the next invoice to issue; the first one when starting |
| End Date | Last date an invoice may be issued for (inclusive). Empty means open-ended |
| Post Automatically | Post each invoice at once instead of leaving it in draft |
| Terms and Conditions | Printed on every generated invoice |

On the **Invoice Lines** tab add the lines. Picking a product fills the
description, unit and price, and the product's sale taxes. Sections and notes
are allowed and are copied to the invoice. The untaxed, tax and total amounts
at the bottom are what each invoice will carry.

The reference (`REC/0001`) is allocated on save.

## 3. Start, pause, resume, finish

- **Start** moves the template to *Running*. It needs at least one real line.
- **Pause** stops the scheduler for this template. The next date is kept.
- **Resume** continues from the kept next date. If that date is already in
  the past, the missed invoices are issued on the next run, one per date. If
  you do not want them, move the next date forward before resuming.
- **Mark as Done** closes the contract. Issued invoices are untouched.
- **Reset to Draft** reopens a finished template for editing.

A template whose next date passes its end date marks itself *Done*.

## 4. What the scheduler does

The scheduled action *Recurring Invoices: generate due invoices* runs once a
day. For each running template whose next date is today or earlier it:

1. looks for an existing, non-cancelled invoice of this template on that date
   and, if there is one, does not create another;
2. otherwise creates a customer invoice dated on the scheduled date with the
   template's lines, posting it when *Post Automatically* is set;
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
