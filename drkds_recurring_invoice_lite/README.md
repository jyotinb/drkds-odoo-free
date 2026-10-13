# Recurring Invoices (Lite)

Issue the same customer invoice on a schedule, on Odoo 19 Community.

A rent, a retainer, a maintenance contract or a subscription is described once
as a template: customer, journal, lines with product, quantity, price and
taxes, and an interval of N days, weeks, months or years. A daily scheduler
turns the template into a real customer invoice on every due date and links
the two.

## What you get

| Piece | What it does |
|---|---|
| Template | Reference from a sequence, name, customer, sale journal, currency, payment terms, terms and conditions, lines, interval, next date, end date, auto-post flag, status |
| Scheduler | Daily job; issues one `out_invoice` per due date, dated on that date, posts it if asked, then advances the next date |
| Generate Now | Issues the next scheduled invoice immediately from the form |
| Trail | `recurring_id` on every generated invoice; smart button, invoice count and last invoice date on the template; invoice search by template |
| Views | List, kanban grouped by status, form with chatter, search with filters and group-bys |
| Security | Billing users (`account.group_account_invoice`) create and run; read-only accounting users read; multi-company record rules |

## Behaviour worth knowing

- **One invoice per template and date, ever.** The scheduler and the Generate
  Now button both check for an existing non-cancelled invoice on the scheduled
  date before creating one. Running the job twice, or pressing the button
  twice, does not duplicate. A cancelled invoice does not block the date.
- **The invoice is dated on the scheduled date, not the day the job ran.** A
  scheduler that was off for three weeks on a weekly template issues three
  invoices, each on its own date, then stops at the first future date.
- **Month-end arithmetic.** The template remembers the day of month it was
  set on. A monthly template set on 31 January invoices on 28 February and is
  back on 31 March. A yearly template set on 29 February 2024 invoices on
  28 February 2025 and on 29 February 2028. Editing the next date by hand
  re-anchors the day.
- **End date is inclusive.** With end date 1 March, the 1 March invoice is the
  last. When the next date moves past the end date the template marks itself
  done and the job skips it.
- **Pause keeps the schedule.** Pausing stops the job; resuming leaves the next
  date where it was, so dates missed while paused are caught up on the next
  run. Move the next date forward before resuming if that is not wanted.
- **Failures are isolated.** If one template cannot be invoiced (a missing
  account, a posting the localisation refuses), the reason is written on that
  template as *Last Scheduler Error*, its next date is left alone so it is
  retried tomorrow, and the job goes on with the other templates. The error is
  cleared on the next success and there is a *Scheduler Error* filter.
- **Deleting is refused** once a template has issued invoices; archive it
  instead.

## How this differs from Odoo's own recurrence

Odoo 19's *Auto-post* on a journal entry duplicates a posted entry monthly,
quarterly or yearly until a date. This module works from an editable template
rather than a posted document, adds daily and weekly intervals and any
multiple, pause and resume, an end date, a Generate Now button, draft-or-post
per template, and a trail you can search on.

## Installation

Copy `drkds_recurring_invoice_lite` into your addons path, update the apps
list and install **Recurring Invoices (Lite)**. Depends on `account` only.

The scheduled action *Recurring Invoices: generate due invoices* is created
active, running once a day. Adjust its time under Settings > Technical >
Scheduled Actions if the default does not suit.

## Configure and use

1. Accounting > Customers > Recurring Invoices > New.
2. Name the contract, pick the customer and journal, add the lines (picking a
   product fills description, price and taxes), set *Repeat Every*, *Next
   Invoice Date* and, if the contract ends, *End Date*. Tick *Post
   Automatically* if the invoices should not wait in draft.
3. **Start.** From then on the scheduler issues the invoices. Use **Pause**,
   **Resume**, **Generate Now** and **Mark as Done** from the form.
4. The **Invoices** smart button lists everything issued from the template.

See `doc/user_manual.md` for the walkthrough.

## Not in this module

No emailing of the generated invoices (use Odoo's own *Send* on the invoice or
its sending cron), no proration for partial periods, no price changes
scheduled ahead, no customer portal for the contract.

The drkds Accounting Pro app adds payment approvals, ageing analysis and
cash-flow reporting.

Part of the drkds Indian SME suite for Odoo 19 Community.
