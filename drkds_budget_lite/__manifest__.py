{
    "name": "Account Budgets (Lite)",
    "summary": "Set a budget per account and period, then track committed and actual spend against it",
    "description": """
Account Budgets (Lite)
======================

Odoo 19 Community ships an accounting settings toggle for budget management but
no budget model behind it. This module supplies one: a budget document with a
period and a company, budget lines against accounts or account groups, and
actual spend read straight from posted journal items.

What you get
------------
* **Budget document** - a name, a period, a company, a responsible user and a
  status of draft, confirmed, done or cancelled. The period is locked once the
  budget is in force, so a variance people have already circulated cannot
  quietly change meaning.
* **Budget lines** - budget one account, or a whole account group such as every
  travel account, with an optional analytic account. The planned figure is
  always entered as a plain positive amount.
* **Actuals from the ledger** - the sum of posted journal items on the covered
  accounts, inside the budget period, in the budget's company. Draft and
  cancelled entries never count.
* **Correct signs** - Odoo stores debits positive and credits negative, so an
  expense accumulates a positive balance and income a negative one. Expense
  lines take the balance as it is, income lines take its negative, and both read
  as positive amounts in the report.
* **Variance, stated favourably** - variance is positive when things are going
  well. An expense line is favourable when actual is below planned, an income
  line when actual is above planned. A line is flagged **over budget** when its
  variance is unfavourable, which means over-spend on an expense line and
  under-collection on an income line.
* **Budget versus Actual report** - a reporting view of every line of every
  confirmed budget, grouped by account out of the box, with filters on period,
  status and direction, and a drill-down button on each line that opens exactly
  the journal items behind the figure.

Multi-company
-------------
Budgets and their lines carry a company and are isolated by record rules, so a
group running several GSTINs as separate companies sees only its own figures.
Actuals are read from the budget's own company only.

Notes
-----
* Amounts are held in the company currency, the currency the journal item
  balances are already stored in.
* A line planned at zero reports a zero percentage rather than failing, because
  a nil budget is a legitimate thing to record.
* Where an analytic account is set, only that analytic account's share of each
  journal item counts, so a 40 percent allocation does not consume the whole
  analytic budget.
* Actual and variance are computed live rather than stored, so a back-dated
  posting is reflected the next time the report is opened.

The drkds Accounting Pro app adds budget revisions with approvals, forecasting
and multi-company consolidation.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Accounting/Accounting",
    "author": "drkds",
    "website": "https://drkdsinfo.com",
    "support": "jyotinboghani@gmail.com",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "security/drkds_budget_security.xml",
        "views/drkds_budget_views.xml",
        "views/drkds_budget_line_views.xml",
        "views/drkds_budget_menus.xml",
    ],
    "images": ["static/description/cover.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
