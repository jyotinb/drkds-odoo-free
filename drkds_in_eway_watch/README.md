# E-Way Bill Expiry Watch and Threshold Reminder (India)

Adds an expired state, expiry filters and a threshold reminder to Odoo's
e-way bill.

## This module does not generate e-way bills

Odoo Community's own **Indian E-waybill** module (`l10n_in_ewaybill`) does
that, through the government channel via a GSP, and it stores the number, the
date and the validity date it gets back. Install and configure that module
first — this one depends on it and is useless without it.

What Odoo's module does not do is act on the validity date it stored:

- its status is only Pending, Generated or Cancelled;
- it ships no scheduled action;
- its views carry no `<filter>` elements at all.

So a bill that lapsed last night still reads "Generated" and nobody finds out
until a vehicle is stopped. This module adds the watch on top, and nothing else.

## What it adds

| Area | Behaviour |
|---|---|
| Expiry status | Active, Expiring Soon, Expired, Cancelled, in a **separate field** beside core's own status |
| Daily job | Refreshes the status and posts one message on each bill that has lapsed |
| Filters | Expiring within 24 hours, within 3 days, already expired, validity differs from rule, cancelled |
| Group-bys | Expiry status, transporter, transport mode, e-way bill date |
| List view | Core ships none; this adds one, with red rows for expired and amber for expiring |
| Threshold reminder | Posted customer documents at or above a configurable amount with no generated e-way bill |
| Validity estimate | One day per 200 km or part thereof, shown beside the portal's date |

### Why the core status still says "Generated"

Because it should. `state` on `l10n.in.ewaybill` records what the portal said
when the bill was created, and its values are driven by API responses. Adding
an "expired" value to a selection another module writes from a government
response would break the moment core changes it. The expiry status is
therefore a field of our own, computed from `ewaybill_expiry_date`, and core's
field is left exactly as it is.

## Validity rule

Rule 138(10) of the CGST Rules: for cargo other than over dimensional cargo an
e-way bill is valid for one day for every 200 km or part thereof, counted from
generation. The 200 km figure replaced the earlier 100 km with effect from
1 January 2021 (Notification 94/2020-Central Tax, amending rule 138). Over
dimensional cargo uses 20 km per day.

Because that figure has changed before and differs by cargo type, kilometres
per day is a **company setting** with a documented default of 200. The estimate
is shown for comparison only: the date that counts is the one the portal
returned.

## Manual entry is deliberately not supported

Core owns `name`, `ewaybill_date` and `ewaybill_expiry_date` as API results and
marks them readonly. Making them writable so a hand-generated number could be
typed in would let a record claim a bill the portal never issued, and would
fight core on the next upgrade. If you generate on the NIC portal by hand,
this module has nothing to hang a watch on.

## Configuration

Accounting → Configuration → Settings → **E-Way Bill Watch (India)**:

- **E-Way Bill Threshold** — default 50,000.
- **Kilometres per Day of Validity** — default 200. Set 20 for over
  dimensional cargo.

## Installation

1. Copy this folder into your Odoo addons path.
2. Update the apps list.
3. Install **E-Way Bill Expiry Watch and Threshold Reminder (India)**.

## Compatibility

Odoo 19 Community. Depends on `l10n_in_ewaybill` only.

## Disclaimer

This module is a tool to assist with compliance workflows. Responsibility for
statutory compliance rests with the user and their tax professional.

The drkds India accounting app adds e-way bill generation through the official
NIC channel, plus GSTR filing and reconciliation.

Part of the drkds Indian SME suite for Odoo 19 Community.
