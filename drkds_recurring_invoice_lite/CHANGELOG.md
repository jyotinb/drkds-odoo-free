# Changelog

## 19.0.1.0.0 - 2026-10-13

First release.

- Recurring invoice template with customer, journal, currency, payment terms,
  lines (product, description, quantity, unit price, taxes, sections and
  notes), interval in days, weeks, months or years, next date, end date and
  auto-post flag, on the mail thread and activity mixins.
- Daily scheduled action issuing one customer invoice per due date, dated on
  the scheduled date, posting it when asked, catching up missed dates, and
  marking the template done past its end date.
- Idempotent generation: never two non-cancelled invoices for the same
  template and date.
- Month-end and leap-year arithmetic anchored on the day the schedule was set.
- Per-template failure isolation with the reason recorded on the template.
- Start, pause, resume, mark as done, reset to draft and Generate Now.
- `recurring_id` on customer invoices, shown in Other Info and searchable.
- List, kanban, form and search views; menu under Accounting > Customers.
- Access for billing and read-only accounting groups; multi-company rules.
