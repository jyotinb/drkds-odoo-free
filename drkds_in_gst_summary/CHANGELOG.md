# Changelog

## 19.0.1.0.1 – 2026-09-17

- Tests: the fixture GSTINs were copied from Odoo's own `l10n_in` test data,
  whose check digits are invalid. Stock Odoo only checks the format so it
  never noticed; with drkds_in_partner_validate installed alongside, which
  does check them, the tests could not set up. The fixtures now carry valid
  check digits. No functional change.

## 19.0.1.0.0 - 2026-09-15  First release.
