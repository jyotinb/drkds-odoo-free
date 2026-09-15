# Changelog

## 19.0.1.0.0 - 2026-09-15

First release.

- Fixed asset record with reference from a sequence, category, purchase date
  and value, salvage value, useful life, depreciation start date, location,
  custodian, supplier, invoice reference and a draft / in service / disposed /
  scrapped status.
- Asset categories carrying the method, period, useful life and salvage
  percentage proposed for new assets.
- Straight line depreciation schedule in yearly or monthly periods, pro-rated
  by month, closing exactly on the salvage value.
- Schedule rebuilt from scratch whenever an input changes; no stale lines.
- A useful life of zero or less, and a salvage value above cost, are refused.
- Disposal and scrapping: schedule truncated at the disposal date, gain or
  loss shown for information.
- Asset register report as at any date, on screen and as a PDF, filtered by
  category, custodian and status.
- Multi-company record rules and a per-company financial year end.
