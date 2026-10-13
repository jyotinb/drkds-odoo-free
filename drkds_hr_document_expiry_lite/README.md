# Employee Document Expiry (Lite)

Employee documents with expiry dates, reminders to HR and a missing-documents
check, on Odoo 19 Community.

Passports, employment contracts, work permits, licences: every employee holds
papers that run out. This module keeps each one on the employee record with
its scan, works out whether it is valid, expiring or expired from the dates,
and reminds the HR responsible before it lapses.

## What you get

| Piece | What it does |
|---|---|
| Document type | Name, *Has Expiry Date*, *Remind Days Before*, *Mandatory for Every Employee*, optional company |
| Employee document | Employee, type, number, issue date, expiry date, attached file, note, status, days left; chatter and tracking |
| Status | Valid, Expiring (inside the type's reminder window), Expired (the day after the expiry date) |
| Employee form | A Documents tab with an editable list, a warning naming the mandatory types still missing, and a smart button counting documents and expired ones |
| Daily job | *Employee Documents: refresh states and remind* recomputes every status and schedules one activity per expiring document |
| Reminder target | The employee's HR Responsible (if still an active user), else the *Document Reminder Fallback* user set in Settings |
| Employee list | *Missing Mandatory Documents* and *Expired Documents* filters |
| Documents menu | List with Valid / Expiring / Expired filters, group by employee, type, status or expiry month; an activity view |

Four types are installed: Passport (90 days), Employment Contract (30 days),
Work Permit (60 days) and Educational Certificate (no expiry). None is
mandatory until you tick it.

## Installation

Copy the module into your addons path, update the apps list and install
**Employee Document Expiry (Lite)**. Depends on `hr` and `mail`.

## Configuration

1. **Employees > Configuration > Document Types** (HR administrator): adjust
   the reminder windows, tick *Mandatory for Every Employee* where it applies,
   add your own types.
2. **Settings > Employees > Employee Documents**: choose the *Document
   Reminder Fallback* user, per company. It receives reminders for employees
   whose HR Responsible is missing or has been archived.
3. On each employee, **Settings tab > HR Responsible** is who normally gets
   the reminders.

## Use

1. Open an employee, **Documents** tab, add a line: type, number, dates,
   file. Or use **Employees > Documents > New** for the full form with
   chatter.
2. The status follows the dates. The nightly job keeps it current and
   schedules the reminder activity when a document enters its window.
3. To renew, open the document, enter the new dates and upload the new scan.
   The old file is replaced, the status returns to Valid and the reminder
   is removed.
4. **Employees** list, filter **Missing Mandatory Documents** to see who
   still has to hand something in; **Expired Documents** for who is overdue.

## Behaviour worth knowing

- A document expiring today is *Expiring*, not *Expired*. It becomes expired
  the next day.
- A type without expiry never changes status; its documents are always Valid.
- The job never creates a second reminder for a document that already has
  one, however often it runs. Marking the activity done and leaving the
  document unchanged means the next run raises it again.
- An employee with an archived document of a mandatory type counts as missing
  it.
- Odoo Community already reminds about a work permit through the employee's
  own *Work Permit Expiration Date* field; this module covers every other
  document and keeps the scan with the dates.

## Security and personal data

Documents and types are visible to HR officers only (`hr.group_hr_user`).
HR officers create and maintain documents; HR administrators
(`hr.group_hr_manager`) maintain the types. Employees do not see their own
documents in the lite edition. Record rules hide one company's documents from
another.

Files are ordinary Odoo attachments stored in your own database. The module
makes no network call and never writes a document number to the server log.

## Tests

`tests/test_document.py` covers the status at frozen dates including the
boundaries, the daily job, the single-reminder rule, the fallback user, the
renewal, the missing-documents search with every operator the ORM uses, the
smart button counts and the access rights. `tests/test_scenario.py` runs
three employees, passports and contracts, through a year with one renewal.

```
odoo-bin -d <db> -i drkds_hr_document_expiry_lite --test-enable --test-tags=/drkds_hr_document_expiry_lite --stop-after-init
```

The drkds HR Documents app adds employee self-service upload, approval of
submitted documents, reminder emails to the employee and a compliance
dashboard.

Part of the drkds Indian SME suite for Odoo 19 Community.
