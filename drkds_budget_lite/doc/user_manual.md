# Account Budgets (Lite) — user manual

## 1. Who this is for

A finance person who wants to set a spending figure per account for a period and
then see, without exporting anything, how much of it has actually been spent.

Menus:

- **Accounting > Accounting > Budgets** — create and maintain budgets.
- **Accounting > Reporting > Budget vs Actual** — the read-only report.

Access follows the standard accounting groups. Billing Administrator (Accountant)
can create and edit; Accounting Manager can also delete; Read-only users see the
report.

## 2. Creating a budget

1. Go to **Budgets** and click **New**.
2. Give it a name people will recognise, for example *FY 2026-27 Operating
   Budget*.
3. Set **From** and **To**. These dates define the window that actual spend is
   measured over. Both days are included.
4. Pick the **Company**. In a multi-company database only journal items of this
   company count.
5. Set the **Responsible** user — the person who answers for the variance.

### Adding lines

In the **Budget Lines** tab, add one line per figure you want to track:

| Field | What to put in it |
|---|---|
| Account | The general ledger account to budget, for example 600100 Travel |
| Account Group | *Instead* of an account, a group such as 6001-6002, covering every account in that code range |
| Analytic Account | Optional. Restricts the line to items carrying this analytic account |
| Planned | The budgeted figure, always a **positive** amount, whether it is a cost or a revenue |
| Description | Optional free text |

A line takes an account **or** a group, never both. If it took both, the same
journal items would be counted twice across the budget.

**Actual**, **Variance**, **Variance %** and **Achieved %** fill in by
themselves. They are never typed.

## 3. The status flow

| Status | Meaning |
|---|---|
| Draft | Still being written. Everything can change. |
| Confirmed | In force and being reported against. The period is locked. |
| Done | The period is closed. Figures stay visible and keep recomputing. |
| Cancelled | Abandoned. |

Use **Confirm** to put a budget in force; it needs at least one line. **Mark
Done** closes it. **Reset to Draft** unlocks the period again — do that before
changing dates on a budget that is already in force. A done budget must be reset
to draft before it can be cancelled, so history is not rewritten by accident.

Only confirmed and done budgets appear in the Budget vs Actual report.

## 4. How actual spend is calculated

A line's actual is the sum of journal items that satisfy **all** of:

- the move is **posted** — draft and cancelled entries are ignored;
- the date is between the budget's From and To dates, inclusive;
- the company is the budget's company;
- the account is the line's account, or falls inside the line's account group
  code prefix range;
- if an analytic account is set, the item carries it in its analytic
  distribution.

Where an analytic account is set, only its share of each item is counted. An
item of 1,000 split 40% to Project B and 60% to Project C contributes 400 to a
Project B budget line, not 1,000.

Figures are computed when you open the view, not stored. A back-dated posting
shows up the next time the budget or report is opened; nothing needs recomputing
by hand.

## 5. Signs and what "over budget" means

Odoo records a debit as a positive balance and a credit as a negative one. So
an expense builds up a positive balance and income a negative one. Neither reads
well in a budget, where both a cost and a revenue target are entered as a plain
positive number.

Each line therefore has a **Direction**, worked out from the accounts it covers.
It is *Income* only when every covered account is an income account, and
*Expense* otherwise — a mixed group is treated as an expense budget, so an
unexpected debit makes the line look worse rather than better.

| Direction | Actual | Variance | Over budget |
|---|---|---|---|
| Expense | the balance as it is | Planned − Actual | Actual **above** Planned (over-spend) |
| Income | the balance negated | Actual − Planned | Actual **below** Planned (under-collection) |

So a **positive variance is always favourable**, in both directions, and the
**Over Budget** flag always means the unfavourable case. Over-budget lines are
shown in red in the lines list and in the report.

Worked examples:

- Travel budget 1,000, posted travel expense 1,250 → Actual 1,250, Variance
  −250, Variance % −25%, over budget.
- Travel budget 1,000, posted travel expense 800 → Variance +200, +20%, fine.
- Service income target 1,000, invoiced 600 → Actual 600, Variance −400, −40%,
  over budget, because you collected less than planned.
- Service income target 1,000, invoiced 1,400 → Variance +400, fine.

**Achieved %** is Actual ÷ Planned, the figure shown on the progress bar. A line
planned at zero reports 0% for both percentages rather than failing.

## 6. The Budget vs Actual report

**Accounting > Reporting > Budget vs Actual** lists every line of every confirmed
and done budget, grouped by account by default.

- Filter by budget status, by direction (Expense or Income), and by period start.
- Regroup by account group, analytic account, budget, direction or company.
- Click the magnifier on any line to open **exactly** the posted journal items
  behind that figure — same accounts, same dates, same company, same analytic
  account. This is the check to run when a number looks wrong.

The same drill-down button is on each line inside the budget form.

## 7. Multi-company

Budgets and their lines carry a company and are protected by global record
rules, so users allowed in one company never see another company's budgets. An
account that does not belong to the budget's company is refused on the line, and
actuals are read from the budget's own company only. Consolidating several
companies into one budget is deliberately not done here.

## 8. Limitations

- Amounts are in the company currency. There is no per-budget currency.
- Budget revisions, an approval workflow, forecasting and multi-company
  consolidation are out of scope for this module.

The drkds Accounting Pro app adds budget revisions with approvals, forecasting
and multi-company consolidation.

Part of the drkds Indian SME suite for Odoo 19 Community.
