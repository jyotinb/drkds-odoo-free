# Changelog

## 19.0.1.0.0 - 2026-09-15

First release.

- Budget document with period, company, responsible user and a draft /
  confirmed / done / cancelled state, with the period locked once in force.
- Budget lines against a single account or an account group's code prefix
  range, with an optional analytic account.
- Actual spend computed from posted journal items inside the period, in the
  budget's company; draft and cancelled entries excluded.
- Direction-aware sign handling: expense lines take the balance as it is,
  income lines take its negative.
- Variance amount and percentage stated favourable-positive, with an over
  budget flag meaning over-spend on expense lines and under-collection on
  income lines.
- Analytic lines count only the analytic account's share of each item.
- Budget vs Actual reporting view grouped by account, with drill-down from a
  line to the underlying journal items.
- Multi-company record rules on both models.
- Models are named `drkds.lite.budget` and `drkds.lite.budget.line` so the
  module can be installed alongside the paid drkds Accounting Pro app, which
  uses the unprefixed names. The two keep entirely separate tables and records.
