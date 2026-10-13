# Changelog

## 19.0.1.0.0 - 2026-10-13

First release.

- Default commission percentage on the user, with a Commission tab on the
  user form for sales and accounting managers.
- Commission rate table per salesperson and product category, with company,
  uniqueness per salesperson, category and company, and a 0-100 check. The
  nearest matching category wins over the default.
- Commission lines written per product line when a customer invoice is
  posted: salesperson, customer, date, product, category, base in company
  currency, rate, amount, paid status and paid date.
- Credit notes write negative lines. Reset to draft and cancel remove the
  invoice's unpaid lines; re-posting recomputes them once, never duplicating.
- Paid lines block reset, cancel and deletion until marked unpaid.
- Mark as Paid and Mark as Unpaid for sales and accounting managers, from the
  list header and the form.
- List, form, pivot, graph and search views; Commissions menu under Sales,
  Commission Rates under Sales > Configuration; Commission smart button on the
  invoice.
- Salespeople see their own lines and rates; sales and accounting managers see
  everything; multi-company record rules.
