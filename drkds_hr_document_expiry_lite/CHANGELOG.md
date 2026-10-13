# Changelog

## 19.0.1.0.0 - 2026-10-13

First release.

- Document types with Has Expiry Date, Remind Days Before, Mandatory for
  Every Employee and an optional company; four seeded: Passport, Employment
  Contract, Work Permit, Educational Certificate.
- Employee documents with employee, type, number, issue and expiry dates,
  attached file, note, Days Left, and a stored Valid / Expiring / Expired
  status computed from the dates and the type's window; chatter and tracking.
- Expiry required when the type says so; expiry never before issue date;
  reminder window never negative; a type in use cannot be deleted.
- Documents tab, missing-mandatory warning and a Documents smart button with
  an expired count on the employee form.
- Daily scheduled action refreshing every status and scheduling exactly one
  Document Expiry activity per expiring document for the HR responsible, else
  the per-company fallback user from Settings.
- Renewal (new expiry date or new file) clears the open reminder.
- Missing Mandatory Documents and Expired Documents filters on employees.
- Documents list, form, search and activity views; Documents menu under
  Employees; Document Types menu under Configuration.
- HR-officer-only access, HR-administrator-only types, multi-company rules.
