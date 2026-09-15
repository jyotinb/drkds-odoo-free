# Changelog

## 19.0.1.0.0 - 2026-09-15

First release.

- MSME registration block on a contact: registered flag, Udyam number,
  enterprise category and registration date.
- Udyam number validated against the UDYAM-XX-00-0000000 format, including the
  state code, and normalised on save.
- Micro and small vendors are covered by the payment clock; medium vendors are
  explicitly excluded, in line with section 15 of the MSMED Act.
- Both statutory periods: 45 days with a written agreement, 15 days without,
  held as company settings and capped at the statutory maximum.
- Per-vendor agreement basis and optional agreed day count.
- MSME due date, days outstanding, days overdue and status on the vendor bill,
  computed from the acceptance date or the bill date.
- Red warning banner on an overdue bill from a micro or small vendor.
- MSME Outstanding Payments report with list, pivot and graph views, ageing
  buckets, grouping by vendor and a filter for breaches in the current Indian
  financial year.
