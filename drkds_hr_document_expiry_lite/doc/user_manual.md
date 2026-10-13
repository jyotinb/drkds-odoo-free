# Employee Document Expiry (Lite) — user manual

## 1. Who can do what

| Role | Odoo group | May |
|---|---|---|
| HR officer | Employees / Officer (`hr.group_hr_user`) | See, add, edit and archive documents; see the types |
| HR administrator | Employees / Administrator (`hr.group_hr_manager`) | All of the above, plus maintain the document types and the setting |
| Everyone else | — | Nothing. Employees do not see their own documents in this edition |

## 2. Set up the document types

**Employees > Configuration > Document Types**. Four come installed:

| Type | Has expiry | Remind days before | Mandatory |
|---|---|---|---|
| Passport | yes | 90 | no |
| Employment Contract | yes | 30 | no |
| Work Permit | yes | 60 | no |
| Educational Certificate | no | — | no |

For each type:

- **Has Expiry Date** — tick for anything that lapses. A document of such a
  type cannot be saved without an expiry date. Untick for certificates and
  the like: no date is asked for, and a document without one is always
  *Valid*. If you enter an expiry date anyway, the status follows it.
- **Remind Days Before** — how many days before the expiry date the document
  turns *Expiring* and the reminder is raised. Zero means on the expiry day
  itself.
- **Mandatory for Every Employee** — tick, and every employee without an
  active document of this type is listed by the *Missing Mandatory
  Documents* filter and flagged on their form.
- **Company** — leave empty to use the type in every company.

Add your own types freely. Archive a type rather than deleting it once it
has documents; deletion is refused while documents refer to it.

## 3. Choose the fallback reminder user

**Settings > Employees > Employee Documents > Document Reminder Fallback**,
per company. Only HR officers (Employees / Officer) of that company are
offered.

Reminders normally go to the employee's **HR Responsible** (employee form,
*Settings* tab). A reminder is only ever given to someone who can open the
document: an active user with HR officer rights and access to the
employee's company. When the HR Responsible is not such a user (archived,
no longer an HR officer, or not allowed in that company), the reminder goes
to this fallback, provided it qualifies itself. With neither, the job skips
that document and notes the fact in the server log, with the document id
only.

## 4. Add a document

Either from the employee: open the employee, **Documents** tab, **Add a
line**. Or from **Employees > Documents > New** for the full form with
chatter and activities.

- **Employee** and **Document Type** — required.
- **Document Number** — the reference printed on the document. It stays in
  your database and is never written to the log.
- **Issue Date**, **Expiry Date** — the expiry cannot be before the issue,
  and is required when the type has an expiry.
- **File** — the scan. One file per document; uploading another replaces it.
- **Note** — anything HR should know.

The title is built as *Type - Employee*. **Days Left** counts from today;
it goes negative once expired.

## 5. Read the status

| Status | When |
|---|---|
| Valid | No expiry date, or the expiry is further away than the reminder window |
| Expiring | Today is within *Remind Days Before* of the expiry date, up to and including the expiry day |
| Expired | The day after the expiry date, onwards |

"Today" is the date in the employee's timezone (employee form, *Work
Information > Timezone*): a document turns *Expired* at the employee's
midnight, not at midnight UTC or in the timezone of whoever looks at it.
**Days Left** counts the same way.

The status is stored and recomputed by the nightly job, so lists, filters and
group-bys use it directly. Changing a type's reminder window, or the
employee's timezone, recomputes the status of the documents concerned at
once. The status cannot be set by hand, by an import or through the API; it
always follows the dates.

## 6. The daily job and the reminders

**Settings > Technical > Scheduled Actions > Employee Documents: refresh
states and remind** runs once a day. It:

1. recomputes the status of every document that has an expiry date,
   archived ones included;
2. for each document now *Expiring* that is not archived, belongs to an
   employee who is not archived, and has no open *Document Expiry* activity,
   schedules one for the HR responsible (or the fallback, see section 3),
   with the expiry date as its deadline and a summary naming the type, the
   employee and the date. The document number is never part of it.

It never creates a second reminder for a document that already carries one,
no matter how often it runs. If the activity is marked done while the
document is left as it is, the next run raises a new one, because the
document is still expiring. The right way to close a reminder is to renew
the document.

Reminders are visible on the document, in the activity view of
**Employees > Documents**, and in the user's activity menu like any other
Odoo activity.

## 7. Renew a document

Open the document, enter the new **Expiry Date** (and issue date and number),
upload the new **File**, save. Changing the expiry date or the file removes
the open reminder; the status recomputes immediately, normally back to
*Valid*. The previous scan is replaced, not kept: if you need the history,
the chatter records the old and new dates, and you can attach the old scan
to the chatter before renewing.

## 8. Find the gaps

On the **Employees** list, two filters are added under *Filters*:

- **Missing Mandatory Documents** — employees without an active document of
  at least one mandatory type of their company. The employee form shows the
  missing types in a yellow box at the top of the Documents tab.
- **Expired Documents** — employees holding at least one expired document.

The **Documents** smart button on the employee form shows the number of
documents and, in red, how many have expired.

## 9. Multi-company

A document belongs to the company of its employee and is hidden from users
working in other companies. A type bound to a company applies only there; a
type without a company applies everywhere.

## 10. Archiving and deleting

- **Archive a document** that is no longer in use: it stays on record, its
  status keeps being refreshed, and it raises no more reminders.
- **Archive an employee** who has left: their documents stay, with an
  up-to-date status, and raise no more reminders.
- **Delete an employee** only when their data must go: their documents are
  deleted with them, together with the scans, the open reminders and the
  chatter.

## 11. Uninstall

Removing the module deletes its tables, the document records and their
attached files, the activity type, the scheduled action and the setting.
Employees are untouched. Export the documents first if you need them.
