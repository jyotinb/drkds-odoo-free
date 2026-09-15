# India Partner Identifier Validation

**Odoo already checks the shape of a GSTIN. This module checks the check
digit, the state against the address, and the PAN against the GSTIN.**

The GSTIN lives in the standard **Tax ID** (`vat`) field, exactly where Odoo's
own Indian localisation reads it from. No second GSTIN field is added.

## Where the structure check comes from

Structure validation is Odoo's own, from `base_vat`. Its `check_vat_in` accepts
the five real GSTIN forms — normal/composite/casual, UN and ON body, NRI, TDS
and TCS — but it is a pattern test only and never verifies the fifteenth
character. This module keeps all five forms working and adds the missing check.

## What this module adds

| Check | What it catches |
|---|---|
| GSTIN check digit | A transposed or invented number that is shaped correctly |
| GSTIN vs state | First two GSTIN digits disagreeing with the address state |
| GSTIN vs PAN | Characters three to twelve of the GSTIN disagreeing with the PAN field |
| PAN | Structure plus the holder-type character in position four |
| IFSC | Eleven characters with the reserved zero in position five |
| PIN code | Six digits, never starting with zero, on Indian addresses only |

## Behaviour

- The check digit is applied **only to the ordinary GSTIN form**, a two digit
  state code followed by a PAN and the letter Z. UN/ON body, NRI, TDS and TCS
  numbers are accepted on Odoo's own pattern check, because the same
  check-digit convention is not confirmed for them and wrongly refusing a real
  registration is worse than missing a typo.
- Input is normalised on save: spaces, dashes, dots and lower case are cleaned,
  and only when the value actually looks like a GSTIN, so a foreign tax id is
  left exactly as typed.
- Blank is always allowed. No identifier is ever made mandatory.
- A duplicate GSTIN shows a notice rather than blocking, because a number is
  sometimes re-keyed onto a second record on purpose.
- GST state codes are ordinary records, so a new state or union territory is a
  data change rather than a code change.

## Installation

1. Copy this folder into your Odoo addons path.
2. Update the apps list.
3. Install **India Partner Identifier Validation**.

No configuration is needed. The GST state code table is loaded on install.

## Compatibility

Odoo 19 Community. Depends on `base_vat` only, which is the same LGPL-3
Community module Odoo's Indian localisation builds on. It coexists with
`l10n_in`: that module's EDI test GSTIN is never check-digit tested.

## Disclaimer

This module is a tool to assist with compliance workflows. Responsibility for
statutory compliance rests with the user and their tax professional.

## Licence

LGPL-3.

The drkds Accounting India app adds GSTR-1 and GSTR-3B preparation, GSTR-2A reconciliation, TDS and TCS with Form 26Q and an E-Way Bill register.

Part of the drkds Indian SME suite for Odoo 19 Community.
