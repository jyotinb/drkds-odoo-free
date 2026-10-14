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

### Fixed during review, before release

- The sentence about the paid app named the wrong app (or an app that does
  not exist). It now names the paid app that extends this module and lists
  only what that app does.
- The status was dated on the UTC day whenever the daily job computed it
  (it runs as OdooBot, which has no timezone): an Indian site's job, run in
  the early IST hours, kept a document that lapsed at midnight IST reading
  Expiring for another day, out of the Expired filter. The status and Days
  Left are now dated in the employee's timezone, whoever or whatever
  computes them.
- A reminder could be assigned, and mailed, to an HR Responsible or fallback
  user who could not open the document: without HR officer rights, or
  without access to the employee's company. Only an active HR officer of the
  document's company is now assigned; the fallback picker offers only such
  users.
- Deleting an employee left the documents' scans (attachments), open
  reminders, chatter and followers behind, keyed to deleted records, because
  the documents went by SQL cascade only. They are now deleted through the
  ORM with the employee.
- Documents of archived (departed) employees still raised reminders, again
  every day after being marked done. They no longer do.
- Archived documents were left out of the daily refresh and kept a stale
  status. They are refreshed now (still without reminders).
- The stored status could be overwritten by an RPC write or an import that
  updates existing documents. It is now always taken from the dates.
- Two tests asserted `assertRaises(Exception)`; they now expect the exact
  database errors. Test employees carry a fixed timezone.
- Documentation said a type without expiry always gives Valid documents; a
  date entered on such a document is honoured, and the documents now say so.
