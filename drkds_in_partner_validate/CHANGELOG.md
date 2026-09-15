# Changelog

## 19.0.1.0.0 - 2026-09-15

First release.

- GSTIN validation: structure and official check digit.
- PAN validation: structure and holder-type character.
- IFSC and Indian PIN code validation.
- Cross-checks: GSTIN state code against the address state, and the PAN
  embedded in a GSTIN against the PAN field.
- Identifier normalisation on save.
- Non-blocking notice when another contact carries the same GSTIN.
- GST state code table with 37 codes, linked to Odoo states.
