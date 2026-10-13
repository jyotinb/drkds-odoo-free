{
    "name": "Employee Document Expiry (Lite)",
    "summary": "Employee documents with expiry dates, reminders to HR and a missing-documents check, on Odoo 19 Community",
    "description": """
Employee Document Expiry (Lite)
===============================

Keeps every employee's passports, contracts, permits and certificates in one
place, with the file attached, and tells HR before any of them run out.

What it gives you
-----------------
* **Document types** - Passport, Employment contract, Work permit and so on.
  Each type says whether it carries an expiry date, how many days before the
  expiry HR should be reminded, and whether every employee must have one.
* **Employee documents** - type, number, issue and expiry date, the scanned
  file, a note, and a state of Valid, Expiring or Expired worked out from the
  dates and the type's reminder window. Chatter and tracking on every record.
* **On the employee form** - a Documents tab and a smart button that counts
  the documents and turns red when any has expired.
* **Daily reminder** - a scheduled action refreshes the states and schedules
  exactly one activity per expiring document for the employee's HR
  responsible, or a fallback user chosen in Settings. Renewing the document
  clears the reminder.
* **Missing mandatory documents** - a filter on the employee list showing who
  still has no document of a mandatory type, plus an Expired documents filter.
* **Lists and searches** - documents by state, type, employee or expiry month;
  an Expiring and an Expired filter; group by anything useful.

Security
--------
Documents are visible to HR officers only. HR officers add and maintain
documents; HR administrators maintain the document types. Employees do not
see their own documents in the lite edition. Files stay as attachments in
your own database; nothing is sent anywhere.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "author": "drkds",
    "website": "https://drkdsinfo.com",
    "support": "jyotinboghani@gmail.com",
    "license": "LGPL-3",
    "depends": ["hr", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "security/drkds_hr_document_rules.xml",
        "data/drkds_hr_document_data.xml",
        "views/drkds_hr_document_type_views.xml",
        "views/drkds_hr_document_views.xml",
        "views/hr_employee_views.xml",
        "views/res_config_settings_views.xml",
        "views/drkds_hr_document_menus.xml",
    ],
    "images": [],
    "installable": True,
    "application": False,
    "auto_install": False,
}
