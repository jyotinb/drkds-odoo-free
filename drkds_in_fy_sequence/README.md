# Indian Financial Year Numbering

Number invoices as `INV/2026-27/0001` and reset the counter every 1 April.

The Indian financial year runs 1 April to 31 March and is written `2026-27`.
GST rules expect a fresh, consecutive invoice series for each financial year.
Odoo's built-in sequence tokens are `strftime` codes, so they can print a
calendar year but not a year that straddles two of them.

## What it adds

- **A financial year token.** `%(fy)s` renders `2026-27` and `%(fy_short)s`
  renders `2627`, anywhere in an `ir.sequence` prefix or suffix. `%(range_fy)s`
  and `%(range_fy_short)s` report the financial year of the subsequence the
  number is drawn from, mirroring Odoo's own `%(range_year)s`.
- **A configurable start month.** April by default, set on the company. Books
  that close on another month shift the whole calculation with one field.
- **A range builder.** An action on the sequence form that creates one
  `ir.sequence.date_range` per financial year, for as many years ahead as you
  want. Safe to re-run; existing years are left alone.
- **A company helper.** `company.drkds_fy_string(date)` returns the financial
  year of any date, so reports and other modules never re-derive it.

## Printing versus restarting

These are two different things. Putting `%(fy)s` in a prefix changes what the
number *looks like*; the counter keeps climbing across the year boundary.
Creating a date range per financial year is what makes the counter genuinely
restart at 1. For a compliant series you want both. The user manual walks
through it.

## Built on Odoo's own mechanism

Nothing here reimplements numbering. The financial year tokens are resolved to
plain text and then handed to the standard `_get_prefix_suffix`, and the
restart uses the stock `use_date_range` and `ir.sequence.date_range` machinery.

## Install

Copy into your addons path and install `drkds_in_fy_sequence`. Depends on
`base` only. Odoo 19 Community.

This module is a tool to assist with compliance workflows. Responsibility for
statutory compliance rests with the user and their tax professional.

The drkds GST suite adds GSTR-1 and GSTR-3B preparation, GSTR-2A
reconciliation and an e-invoice workflow.

Part of the drkds Indian SME suite for Odoo 19 Community.

License: LGPL-3.
