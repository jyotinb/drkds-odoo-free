# Changelog

## 19.0.1.0.0 - 2026-09-15

First release.

- GSTIN check digit, added on top of the structure check Odoo's own `base_vat`
  already performs. All five GSTIN forms core accepts keep working; the check
  digit is applied only to the ordinary form.
- The GSTIN is read from the standard Tax ID (`vat`) field. No second GSTIN
  field is introduced.
- Cross-checks: GSTIN state code against the address state, and the PAN
  embedded in a GSTIN against the PAN field.
- PAN validation: structure and holder-type character.
- IFSC and Indian PIN code validation.
- Identifier normalisation on save, applied to a `vat` only when it looks like
  a GSTIN.
- Non-blocking notice when another contact carries the same GSTIN.
- GST state code table with 37 codes, linked to Odoo states.
