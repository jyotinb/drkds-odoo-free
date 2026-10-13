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

### Fixed during review, before release

- Generated invoices ignored the customer's fiscal position: the template's
  taxes were copied as they were, so an inter-state customer got CGST+SGST
  instead of IGST and an export customer was charged 18%. Each invoice now
  maps the template's taxes through its own fiscal position.
- Picking a product on a template in a foreign currency used the list price
  as it stood (25,000 INR became 25,000 EUR). The price is now converted into
  the template's currency.
- A branch could not use the module: no journal was offered or defaulted and
  the product's taxes were dropped, because the domains and defaults looked
  only at the branch itself. Parent company journals, taxes, products and
  customers now apply, as on the branch's own invoices.
- The scheduler read "today" in UTC (OdooBot's zone), so a job running at
  23:30 UTC issued an Indian template's invoice a day late. It now reads the
  date in the time zone of each template's salesperson.
- The scheduler failed outright, or silently skipped the other companies,
  when the scheduled action was set to run as a user without accounting
  rights in every company. It now serves every company whatever its user.
- The company's default terms and conditions were removed from every
  generated invoice, and the customer's payment terms were not used. The
  payment terms now default from the customer; empty conditions keep the
  company default.
- An invoice without payment terms was due on the day it was generated, so a
  catch-up or early Generate Now produced a due date before or after the
  invoice date. It is now due on its own date.
- A purchase journal could be saved on a template; every run then failed. The
  journal must be a sales journal.
- A finished template reset to draft could be started with its next date
  after its end date, and Generate Now then claimed to have marked it done
  while the error rolled that back. Start is refused until the dates are put
  right, and the message no longer claims a change.
- A running template without lines could be created or written directly
  (import, API, a default_state in the context) and issued an empty invoice
  every period. The rules Start applies are now constraints.
- Default values in the caller's context (default_state and the like) leaked
  into the invoice created by Generate Now and could make it fail.
- Salespeople, who read invoices but not templates, met an access error when
  searching invoices by template. The *Recurring Template* field on invoices
  is now limited to billing and read-only accounting users.
- Read-only accounting users were shown Start, Pause, Generate Now and the
  other action buttons, which then failed. The buttons are hidden from them.
- A template created without a next date (import, API) had no anchor day, so
  a schedule set on the 31st drifted to the 28th after February.
