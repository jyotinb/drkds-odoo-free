# Fixed Asset Register (Lite)

A place to record what your business owns, who holds it, and what it is worth
on paper on any given day.

Odoo 19 Community ships no fixed asset register. Most small businesses end up
keeping one in a spreadsheet: a list of assets, a straight line calculation,
and a written down value at year end for the accountant. This module is that
spreadsheet, done properly, inside Odoo.

**This register does not post to your accounts.** It computes and reports. The
depreciation journal entry stays a manual entry made by whoever closes your
books.

## What it does

- **The asset** — description, an automatic reference, category, purchase date
  and value, salvage value, useful life in years or months, depreciation start
  date, location, custodian, supplier and invoice reference, with a status of
  draft, in service, disposed or scrapped.
- **Categories** — carry the useful life, period and salvage percentage
  proposed for new assets. Editing a category never rewrites an asset that has
  already been entered.
- **The schedule** — straight line, in financial years or calendar months,
  shown on the asset as period, opening value, depreciation, accumulated
  depreciation and closing written down value.
- **Disposal** — record the date and the proceeds; the schedule stops there and
  the gain or loss against the written down value is shown for information.
- **The register report** — every asset with its written down value as at a
  date you choose, on screen or as a PDF, filtered by category, custodian and
  status.

## Getting the arithmetic right

Periods are measured in months rather than days, so a full year of a leap year
is worth exactly one year of depreciation and no more. A mid-year purchase is
pro-rated across the first and last periods. The final period absorbs every
rounding remainder, so a schedule that runs its course closes on the salvage
value to the cent.

The schedule is derived data: change the value, the life or the start date and
it is rebuilt from scratch, never patched. A useful life of zero or less is
refused with a message that says why.

## Installation

Drop the module in your addons path, update the apps list and install
**Fixed Asset Register (Lite)**. Depends on `base` and `mail` only.

Give your users the **Fixed Assets / Reader** or **Fixed Assets / Manager**
group. Set the financial year end on each company under
*Settings › Companies*; it is what cuts the yearly periods.

## Not in this module

Posting depreciation entries to the ledger, written down value and other
non-straight-line methods, asset revaluation and component splitting are
deliberately not here.

The drkds Accounting Pro app adds posted depreciation entries, reducing balance
and other methods, revaluation and asset components.

## Alongside the paid app

This module and the paid drkds Accounting Pro app can be installed in the same
database: their models are named differently (`drkds.lite.asset` here) and each
keeps its own records. Nothing is migrated between them, so assets entered here
do not appear in the paid app and would have to be re-entered.

Part of the drkds Indian SME suite for Odoo 19 Community.
