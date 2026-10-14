# Changelog

## 19.0.1.0.2 – 2026-10-14

- Security: a wizard could be read or changed by another user holding the
  same access right, since Odoo 19 gives wizard records no protection of
  their own. Each wizard is now kept to the user who opened it. Upgrade the
  module to apply the rule.

## 19.0.1.0.1 – 2026-09-17

- Tests: the fixture GSTINs were copied from Odoo's own `l10n_in` test data,
  whose check digits are invalid. Stock Odoo only checks the format so it
  never noticed; with drkds_in_partner_validate installed alongside, which
  does check them, the tests could not set up. The fixtures now carry valid
  check digits. No functional change.

## 19.0.1.0.0 - 2026-09-15  First release.
