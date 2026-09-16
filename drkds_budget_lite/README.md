# Account Budgets (Lite)

Set a budget per account and period, then track actual spend against it from
posted journal items.

Odoo 19 Community ships an accounting settings toggle for budget management but
no budget model behind it. This module supplies one.

## What it does

| Piece | Behaviour |
|---|---|
| Budget document | Name, period, company, responsible user, status (draft, confirmed, done, cancelled) |
| Budget line | One account **or** one account group, an optional analytic account, and a planned amount |
| Actual | Sum of **posted** journal items on the covered accounts, inside the period, in the budget's company |
| Variance | Planned versus actual, as an amount and a percentage, with an over-budget flag |
| Report | Budget vs Actual view grouped by account, with drill-down to the journal items |

## The sign convention

Odoo stores every journal item as a signed `balance`: debit positive, credit
negative. An expense therefore accumulates a positive balance and income a
negative one. A budget report has to show both as positive amounts, so each line
carries a direction taken from the accounts it covers:

| Direction | Actual | Variance | Over budget means |
|---|---|---|---|
| Expense | `sum(balance)` | `planned - actual` | actual above planned — over-spend |
| Income | `-sum(balance)` | `actual - planned` | actual below planned — under-collection |

Variance is therefore **favourable positive** in both directions: a positive
number is always good news. A line is flagged over budget when its variance is
negative.

A group that mixes income and expense accounts is treated as an expense budget.
That is the cautious reading — an unexpected debit should make the line look
worse, not better.

## What counts towards an actual

- Moves in state `posted` only. Draft and cancelled entries are ignored, because
  a proposal that can move a variance is how a budget report loses the finance
  team's trust.
- Dates from `date_from` to `date_to`, both days included.
- The budget's own company only.
- The chosen account, or every account whose code falls inside the chosen
  account group's prefix range.
- Where an analytic account is set, only that analytic account's share of each
  item — a 40% allocation contributes 40% of the balance.

## Multi-company

Budgets and lines carry a company and are isolated by global record rules, so a
group running several GSTINs as separate companies sees only its own figures.
An account belonging to another company is refused on the line.

## Notes

- Amounts are in the company currency, the currency balances are already stored
  in.
- A line planned at zero reports a zero percentage instead of dividing by zero.
  A nil budget is a legitimate thing to record.
- Actual and variance are computed live, not stored, so a back-dated posting is
  reflected the next time the view is opened.
- The period of a confirmed or done budget cannot be changed. Reset it to draft
  first.

## Installation

1. Copy this folder into your Odoo addons path.
2. Update the apps list.
3. Install **Account Budgets (Lite)**.

Budgets appear under Accounting > Accounting > Budgets, and the report under
Accounting > Reporting > Budget vs Actual.

## Compatibility

Odoo 19 Community. Depends on `account` only.

The drkds Accounting Pro app adds budget revisions with approvals, forecasting
and multi-company consolidation.

## Alongside the paid app

This module and the paid drkds Accounting Pro app can be installed in the same
database: their models are named differently (`drkds.lite.budget` here) and each
keeps its own records. Nothing is migrated between them, so budgets entered here
do not appear in the paid app and would have to be re-entered.

Part of the drkds Indian SME suite for Odoo 19 Community.
