# Changelog

## 19.0.1.0.0 - 2026-10-13

First release.

- Default commission percentage on the user, with a Commission tab on the
  user form for sales and accounting managers.
- Commission rate table per salesperson and product category, with company,
  uniqueness per salesperson, category and company, and a 0-100 check. The
  nearest matching category wins over the default; a branch also uses its
  parent company's rates.
- Commission lines written per product line when a customer invoice is
  posted: salesperson, customer, date, product, category, base in company
  currency as booked, rate, amount, paid status and paid date.
- Credit notes write negative lines; one made from an invoice takes back at
  the rate that invoice earned. Reset to draft and cancel remove the
  invoice's unpaid lines; re-posting recomputes them once, never duplicating.
- Paid lines are never changed or deleted; resetting, cancelling or changing
  the salesperson of a paid invoice writes the difference as unpaid lines.
- Mark as Paid and Mark as Unpaid for sales and accounting managers, from the
  list header and the form.
- List, form, pivot, graph and search views; Commissions menu under Sales,
  Commission Rates under Sales > Configuration; Commission smart button on the
  invoice.
- Salespeople see their own lines and rates; sales and accounting managers see
  everything; multi-company record rules.

### Fixed during review, before release

- The sentence about the paid app named the wrong app (or an app that does
  not exist). It now names the paid app that extends this module and lists
  only what that app does.
- A credit note made from an invoice took back at the rates in force when the
  credit note was posted. After a rate rise it took back more than was
  earned, and for an invoice that earned nothing (no rate at the time) it
  still took commission back. It now takes back at the invoice's own rate,
  from the salesperson who earned it, and only on products that earned.
- The base of a foreign-currency line was re-converted from the rate table at
  the invoice date instead of using the amount booked. A rate typed on the
  invoice was ignored, and a credit note posted after the table moved took
  back a different amount than its invoice earned (half, in the tested case),
  leaving commission on a fully refunded sale. The base is now the booked
  company-currency amount.
- An invoice whose commission had been marked paid could not be reset to
  draft or cancelled, which blocked billing users without sales rights. The
  documented way round (mark unpaid, then reset) deleted the record of the
  payment and paid the commission a second time on re-posting. Paid lines are
  now kept, the paid amount is taken back with unpaid lines, and deleting
  such an invoice is refused (cancel it instead). Editing a draft invoice no
  longer deletes the paid line of an invoice line that is removed.
- Changing the salesperson on a posted invoice left the commission with the
  old salesperson. It now moves.
- Invoices of a branch ignored the category rates set on its parent company
  and fell back to the default rate.
- A sales or accounting manager could rewrite a line's amount, rate,
  salesperson or status through RPC, including on their own commission.
  Lines are now read-only for everyone; the Mark as Paid / Unpaid buttons
  check the user's rights and write as the system.
- Every internal user could read every salesperson's default rate. The rate
  fields on the user are now restricted to sales and accounting managers,
  while each user can still read their own.
- The commission fields added to invoices had no access groups. The invoice
  form itself was safe (the smart button carries groups), but users who cannot
  read commission lines (a read-only accountant, a purchase user) were offered
  the fields and got an access error whenever they were read, for instance in
  an export. They are now restricted to users who can read commission lines.
- With another commission module installed in the same database, the
  invoice's *Commission* smart button showed that module's count (0) and hid
  itself: both added a field named `drkds_commission_count` to invoices, and
  the one loaded last replaced the other. The button now reads
  `drkds_commission_line_count`, which belongs to this module alone.
- Grouped lists added rates up: a salesperson's row showed 31.00 in
  *Rate (%)* for nine lines at 3 and 5%, the *Commission Rates* groups showed
  the sum of each salesperson's category rates, and the pivot offered that sum
  as a measure. Rates are no longer aggregated; base and commission still are.
