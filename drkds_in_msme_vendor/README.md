# MSME Vendor Payment Tracking (India)

Flag micro and small vendors, watch the 45 day payment clock and list what is
overdue.

Odoo 19 Community · LGPL-3 · depends on `account` only.

## Why

Section 43B(h) of the Income Tax Act, 1961 (inserted by the Finance Act, 2023,
effective from assessment year 2024-25) disallows the deduction for an expense
owed to a **micro or small** enterprise until the amount is actually paid, if
it was not paid inside the limitation period of section 15 of the MSMED Act,
2006. That period is:

| Situation | Limit |
| --- | --- |
| A written payment agreement exists | The agreed period, capped at **45 days** from the day of acceptance |
| No written agreement | **15 days** from the day of acceptance (the "appointed day", section 2(b)) |

**Medium enterprises are not covered.** They register under the MSMED Act and
hold a Udyam number, but section 15 speaks only of micro and small suppliers,
so section 43B(h) does not reach them. Treating a medium vendor as covered is
the most common error in MSME tracking, and this module refuses to make it.

## What you get

- **On the contact**, an MSME tab: registered flag, Udyam registration number,
  enterprise category, registration date, whether a written payment agreement
  exists and an optional agreed day count.
- **Udyam validation** against the published format `UDYAM-XX-00-0000000`
  (prefix, two letter state code, two digit district code, seven digit serial),
  including a check that the state code is a real Indian state or union
  territory. Numbers are normalised on save, so a pasted
  `udyam dl 02 0012345` becomes `UDYAM-DL-02-0012345`. Blank is always allowed.
- **On a vendor bill**, an acceptance date (defaulting to the bill date), the
  MSME due date, the limit applied, days outstanding and a status of Within
  Limit, Due Soon or Overdue. Only for registered micro and small vendors.
- **A red banner** on an overdue bill, naming the due date and the days lost.
- **MSME Outstanding Payments** under Accounting → Reporting: a list, pivot and
  graph of posted, unpaid bills owed to micro and small vendors, grouped by
  vendor, with ageing buckets and a *Breaching, Current Financial Year* filter
  on the Indian April-to-March year.

## Settings

Accounting → Configuration → Settings → **MSME Payment Clock (India)**:

- days with a written agreement (default 45, cannot be set higher),
- days without a written agreement (default 15, cannot be set higher),
- the due soon window (default 7 days).

They are per company. Changing one immediately reprices the MSME due date on
existing vendor bills.

## What this module deliberately does not do

It does not compute the section 43B(h) disallowance and it does not compute the
section 16 interest liability. Those depend on the year of actual payment, the
accounting method and positions your adviser takes. This is a tracking tool: it
keeps the clock and gives you the evidence.

There are no government portal calls of any kind. Udyam validation is offline
and structural.

## Tests

```
odoo-bin -d <db> -i drkds_in_msme_vendor \
  --test-enable --stop-after-init
```

## Disclaimer

This module is a tool to assist with compliance workflows. Responsibility for
statutory compliance rests with the user and their tax professional.

The drkds Accounting India app adds GSTR-1 and GSTR-3B preparation, GSTR-2A reconciliation, TDS and TCS with Form 26Q and an E-Way Bill register.

Part of the drkds Indian SME suite for Odoo 19 Community.
