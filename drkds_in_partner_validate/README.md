# India Partner Identifier Validation

Validate GSTIN, PAN, IFSC and PIN code on contacts, with GSTIN checksum and
state cross-check.

Wrong Indian identifiers are caught at save time, so bad data never reaches an
invoice, a return working paper or a payment file.

## What it checks

| Identifier | Check |
|---|---|
| GSTIN | 15 character structure and the official check-digit algorithm |
| PAN | Five letters, four digits, one letter, plus the holder-type character |
| IFSC | Eleven characters with the reserved zero in position five |
| PIN code | Six digits, never starting with zero, on Indian addresses only |
| GSTIN vs state | First two GSTIN digits must match the state on the address |
| GSTIN vs PAN | Characters three to twelve of the GSTIN must equal the PAN |

## Behaviour

- Input is normalised on save: spaces, dashes, dots and lower case are cleaned.
- Blank is always allowed. No identifier is ever made mandatory.
- A duplicate GSTIN shows a notice rather than blocking, because branches of one
  business legitimately share a PAN.
- GST state codes are ordinary records, so a new state or union territory is a
  data change rather than a code change.

## Installation

1. Copy this folder into your Odoo addons path.
2. Update the apps list.
3. Install **India Partner Identifier Validation**.

No configuration is needed. The GST state code table is loaded on install.

## Compatibility

Odoo 19 Community. Depends on `base` only.

## Disclaimer

This module is a tool to assist with compliance workflows. Responsibility for
statutory compliance rests with the user and their tax professional.

## Licence

LGPL-3.

Part of the drkds Indian SME suite for Odoo 19 Community.
