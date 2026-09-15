# User manual — Indian Financial Year Numbering

## 1. Set the financial year start month

Settings > Users & Companies > Companies, open your company. The field
**Financial Year Starts** sits next to the currency. It is **April** out of the
box, which is what Indian businesses need. Change it only if your books
genuinely close on another month; every calculation in this module follows it.

With April selected:

| Date | Financial year |
| --- | --- |
| 31 March 2026 | 2025-26 |
| 1 April 2026 | 2026-27 |
| 25 December 2026 | 2026-27 |

## 2. Put the financial year in a sequence

Turn on the developer mode, then Settings > Technical > Sequences. Open the
sequence you want — for customer invoices it is usually the one whose code
starts with `account.move`.

In **Prefix**, write:

```
INV/%(range_fy)s/
```

Set **Sequence Size** to 4 so numbers are padded to `0001`.

Tokens this module adds:

| Token | Renders | Based on |
| --- | --- | --- |
| `%(fy)s` | `2026-27` | the document's date |
| `%(fy_short)s` | `2627` | the document's date |
| `%(range_fy)s` | `2026-27` | the date range the number came from |
| `%(range_fy_short)s` | `2627` | the date range the number came from |
| `%(current_fy)s` | `2026-27` | today |
| `%(current_fy_short)s` | `2627` | today |

They mix freely with Odoo's own tokens, so `INV/%(fy_short)s/%(month)s/` works.
Prefer `%(range_fy)s` once you have created date ranges (step 3) — it is the
one that agrees with the counter in every edge case, exactly as Odoo
recommends `%(range_year)s` over `%(year)s`.

## 3. Printing the year is not the same as restarting the counter

**This is the part people get wrong.**

A token in the prefix only changes *how the number is printed*. The counter
behind it is a single running counter. If you stop at step 2, your first
invoice of 2027-28 comes out as `INV/2027-28/0413` — the right year, the wrong
number. GST expects a series that starts at 1 each financial year.

What actually restarts the counter is Odoo's **date range** mechanism: with
**Use subsequences per date_range** ticked, the sequence keeps a separate
counter for each `ir.sequence.date_range` record. Odoo's own ranges are
calendar years, 1 January to 31 December, which is not what you want.

## 4. Build the financial year ranges

On the sequence form, press **Build Financial Year Ranges**, or go to
Settings > Technical > Financial Year Sequence Ranges.

- **Sequence** — the sequence to fix.
- **Start From** — any date inside the first financial year you want. Enter
  `15/08/2026` and you still get the whole 1 April 2026 – 31 March 2027 range.
- **Number of Years** — how many consecutive years to create. Three is a
  sensible choice; re-run the wizard whenever you need more.
- **Preview** — what the first number of that year will look like.

Press **Build Ranges**. The wizard ticks *Use subsequences per date_range*,
creates one range per financial year running from the first day of your start
month to the day before the next one, and skips any year that already has a
range — so it is safe to press twice.

The result:

```
INV/2026-27/0001, INV/2026-27/0002, ... INV/2026-27/0412   (to 31 March 2027)
INV/2027-28/0001                                            (from 1 April 2027)
```

## 5. Using the helper from your own code

```python
fy = self.env.company.drkds_fy_string(invoice.invoice_date)        # '2026-27'
short = self.env.company.drkds_fy_short_string(invoice.invoice_date)  # '2627'
start, end = self.env.company.drkds_fy_bounds(invoice.invoice_date)
```

Useful in report headers, file names for returns, and anywhere a period label
is needed.

## 6. Things to know

- Changing the start month does not renumber documents already issued. Change
  it before a year opens, not in the middle of one.
- A range you have already drawn numbers from keeps its counter. Deleting a
  range to "start again" loses the count; set **Next Number** on the range
  instead.
- Backdating a document to an earlier financial year draws from that year's
  counter, which is the correct behaviour but can produce a number out of
  chronological order. Odoo warns about this independently.
- The module never touches numbers already assigned to existing records.

This module is a tool to assist with compliance workflows. Responsibility for
statutory compliance rests with the user and their tax professional.
