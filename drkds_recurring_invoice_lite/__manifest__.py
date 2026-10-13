{
    "name": "Recurring Invoices (Lite)",
    "summary": "Issue the same customer invoice on a schedule: daily, weekly, monthly or yearly, on Odoo 19 Community",
    "description": """
Recurring Invoices (Lite)
=========================

A retainer, a rent, a subscription, a maintenance contract: the same invoice
goes out to the same customer at a fixed interval. This module keeps that
invoice as a template and issues it on schedule, so nobody has to remember.

What it does
------------
* **A template per contract.** Customer, journal, currency, the invoice lines
  with product, description, quantity, unit price and taxes, and the schedule:
  every N days, weeks, months or years, starting on a date, optionally ending
  on another.
* **A daily scheduler.** Every running template whose next date has arrived
  becomes a real customer invoice carrying its lines, dated on the scheduled
  date. The template then advances to the following date. Templates past their
  end date are marked done.
* **Auto-post, or not.** A template can leave its invoices in draft for a
  review, or post them straight away.
* **Never twice.** One invoice per template and date, however many times the
  scheduler runs or the button is pressed. A scheduler that was down for a
  while catches up, one invoice per missed date, without duplicating.
* **Month-end arithmetic that holds.** A monthly template anchored on the 31st
  invoices on 28 February and returns to the 31st in March; a yearly one
  anchored on 29 February falls back to the 28th in common years.
* **Pause and resume** without losing the schedule, and **Generate now** to
  issue the next invoice ahead of time.
* **A trail both ways.** Every generated invoice links back to its template,
  and the template shows its invoices on a smart button, with the date of the
  last one and the count.

Fields
------
Reference, name, customer, journal, currency, payment terms, interval number
and unit, next date, end date, auto-post, status, lines, last invoice date,
invoice count, untaxed, tax and total amounts.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "author": "drkds",
    "website": "https://drkdsinfo.com",
    "support": "jyotinboghani@gmail.com",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "security/drkds_recurring_invoice_security.xml",
        "data/ir_sequence_data.xml",
        "data/ir_cron_data.xml",
        "views/drkds_recurring_invoice_views.xml",
        "views/account_move_views.xml",
    ],
    "images": [],
    "installable": True,
    "application": False,
    "auto_install": False,
}
