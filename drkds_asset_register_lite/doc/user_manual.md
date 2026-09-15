# Fixed Asset Register (Lite) — user manual

## What this module is for

You own things that last: vehicles, machines, computers, furniture. Your
accountant needs to know what they cost, how much of that cost has been used up,
and what they are worth on the books at the year end. This module keeps that
list and does the arithmetic.

It is a register and a report. **It does not post anything to your accounts.**
The depreciation journal entry is still made by hand by whoever closes your
books. Nothing in this module touches a ledger.

## Before you start

1. Install the module and give your users a group under
   *Settings › Users & Companies › Users*:
   - **Fixed Assets / Reader** — can look at the register and print it.
   - **Fixed Assets / Manager** — can record assets, categories and disposals.
2. Set your financial year end under *Settings › Companies › your company ›
   General Information › Fixed Asset Register*. It defaults to 31 March. This
   is the boundary yearly depreciation periods are cut on, so get it right
   before you enter assets.

## Step 1 — set up categories

*Fixed Assets › Configuration › Asset Categories*

A category is a class of asset: Vehicles, Plant and Machinery, Office
Equipment. It carries the figures a new asset in that class should start from:

- **Depreciation Method** — straight line. It is the only method here.
- **Period** — yearly or monthly. Yearly gives you one line per financial year,
  which is what most accountants want. Monthly is useful for short-lived assets.
- **Useful Life** — a number and a unit, years or months.
- **Salvage %** — what you expect the asset to still be worth at the end, as a
  percentage of what you paid.

These are proposals only. Once an asset exists it keeps its own figures, so
editing a category later never quietly rewrites a schedule you already checked.

## Step 2 — record an asset

*Fixed Assets › Register › Assets › New*

Pick the category first and the depreciation fields fill themselves in. Then:

| Field | What to put in it |
| --- | --- |
| Asset | What it is, in plain words: "Delivery Van — MH12 AB 1234". |
| Reference | Allocated for you, `FA/2026/0001`. |
| Purchase Date / Value | What the invoice says, before depreciation. |
| Salvage Value | What you expect to get for it at the end. Zero is fine. |
| Useful Life | How long you expect to use it, in years or months. |
| Depreciation Start Date | Usually the date it was put to use, which may be later than the purchase date. |
| Location / Custodian | Where it is and who is answerable for it. |
| Supplier / Invoice Reference | So you can find the paperwork again. |

Save, then press **Put Into Service**. The asset moves from Draft to In
Service. A draft asset shows its schedule so you can check it, but it is
treated as not yet depreciating and is left out of the register.

## Step 3 — read the schedule

The **Depreciation Schedule** tab shows one line per period:

- **Period** — the dates the line covers.
- **Opening Value** — the book value at the start of the period.
- **Depreciation** — the charge for that period.
- **Accumulated Depreciation** — everything written off to the end of it.
- **Closing Written Down Value** — what the asset is worth on the books after.

Three things worth knowing about the arithmetic:

- **Mid-year purchases are pro-rated.** An asset put to use on 1 October with a
  31 March year end gets six months in its first period and the balance in a
  final stub period. A three year life becomes four lines, not three.
- **Leap years do not distort anything.** Periods are measured in months, not
  days, so twelve months is twelve months whatever the calendar did.
- **The last period closes exactly on the salvage value.** Every rounding
  remainder is absorbed at the end, so you never see a schedule that finishes a
  cent or two off.

Change the value, the life, the start date or the period and the schedule is
rebuilt from scratch. There is a **Recompute Schedule** button if you want to
force it. A useful life of zero or less is refused with a message; so is a
salvage value higher than what you paid.

## Step 4 — dispose of an asset

Press **Dispose** on an asset in service and fill in:

- **Disposal Date** — when it left the business.
- **Scrapped** — tick this if it was written off rather than sold. Proceeds are
  then ignored and the whole remaining book value is the loss.
- **Proceeds** — what you sold it for.

Before you confirm, the wizard shows the written down value on that date and
the resulting gain or loss. On confirmation the schedule is truncated at the
disposal date — it stops there rather than running on to the end of a life the
asset never saw out — and the gain or loss is stored on the asset for
information. Nothing is posted.

**Reset to Draft** clears a disposal and restores the full schedule if you
recorded one by mistake.

## Step 5 — print the register

*Fixed Assets › Reporting › Asset Register*

This is what you send your accountant. Choose:

- **As At** — any date. It does not have to be a period end; the value is
  pro-rated inside the period the date falls in.
- **Assets** — in service, all, or only the disposed and scrapped ones.
- **Include Fully Depreciated** — untick to drop assets already written down to
  their salvage value.
- **Categories** and **Custodian** — to narrow it down.

**View Register** shows the result on screen with totals you can group and
export. **Print** gives you the PDF: reference, description, category,
custodian, purchase value, accumulated depreciation and written down value,
with a total row.

An asset disposed of before the date you chose is shown frozen at its disposal
value, not depreciated on past it.

## Searching and grouping

The asset list filters by status — Draft, In Service, Disposed, Scrapped — and
searches on name, reference, category, custodian, supplier and location. Group
by status, category, custodian or purchase date. Grouping by custodian and
printing the list is the quickest way to run a physical verification.

## Multi-company

Assets, categories and schedules belong to a company and are only visible to
users of that company. The financial year end is set per company, so a group
with different year ends across its entities gets the right period boundaries
in each.

## What this module does not do

Posting depreciation entries to the ledger, written down value and other
non-straight-line methods, asset revaluation and component splitting are
deliberately not included.

The drkds Accounting Pro app adds posted depreciation entries, reducing balance
and other methods, revaluation and asset components.

Part of the drkds Indian SME suite for Odoo 19 Community.
