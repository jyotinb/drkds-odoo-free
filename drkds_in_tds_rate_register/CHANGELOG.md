# Changelog

## 19.0.1.0.1 – 2026-09-17

- Tests: no longer inherit Odoo's `l10n_in` test common, whose company and
  partner GSTINs have invalid check digits. Stock Odoo only checks the format
  so it never noticed; with drkds_in_partner_validate installed alongside,
  which does check them, the tests could not set up. The Indian company is
  now built by the tests themselves with valid numbers. No functional change.

## 19.0.1.0.0 - 2026-09-15  First release.
