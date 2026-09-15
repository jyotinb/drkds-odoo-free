# Changelog

## 19.0.1.0.0 - 2026-09-15

First release.

- GST state codes printed beside the supplier state, the buyer state, the
  shipping state and the place of supply, from `res.country.state.l10n_in_tin`.
- Bank block on the invoice footer with account holder, account number, IFSC
  and branch, falling back to the company's own first bank account when the
  invoice has no recipient bank.
- Configurable declaration text on the company, with a default, editable in
  Accounting settings.
- Signature block naming the company.
- Reverse charge marker, driven by `account.tax.l10n_in_reverse_charge`.
- All extras gated on an Indian, GST registered company, matching the condition
  `l10n_in` uses for its own GST blocks.
