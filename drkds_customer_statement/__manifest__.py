{
    "name": "Customer and Vendor Statements",
    "summary": "Statement of account PDF per partner: opening balance, running balance, ageing buckets, sent from the contact",
    "description": """
Customer and Vendor Statements
==============================

A statement of account is the document a customer asks for when they want to
reconcile what they owe you, and the one you send at month end to prompt
payment. Odoo 19 Community has a partner ledger on screen but no printable or
mailable statement. This module adds one.

What it does
------------
* **Statement wizard from Contacts.** Select one or many contacts, pick a date
  range, choose *Activity* (every posted receivable movement in the period) or
  *Outstanding only* (what is still unpaid at the end date), and optionally
  include the vendor side so a partner who is both customer and supplier gets
  one net statement.
* **One PDF per partner.** Opening balance, one line per document with date,
  document number, reference, due date, debit, credit and running balance,
  closing balance, and ageing buckets 0-30, 31-60, 61-90 and 90+ days as at
  the end date.
* **Company currency throughout.** A foreign-currency item is shown at the
  company-currency value of its journal item, with its amount in the original
  currency noted on the line (the amount still open, on an *Outstanding only*
  statement), so the running balance is a single ledger figure.
* **Ageing as at a date, not as of now.** Outstanding amounts are worked out
  from the partial reconciliations dated on or before the end date, so a
  statement reprinted for an earlier date shows what was open then.
* **Send by Email.** Emails each statement to the contacts you selected, with
  a mail template you can edit, and logs it with the PDF on the company's
  chatter. Followers of the contact are not mailed. Needs the Invoicing
  (Billing) right; Accounting read-only users can print.
* **Company and branches.** A company's statement includes its branches,
  which are the same legal entity.
* **Partner form.** A *Statement* smart button, and four ageing fields
  (computed when read, never stored) with the total due, for Billing and
  Accounting read-only users.
* **Settings.** Choose the company bank account printed on the statement and
  a footer note, under Invoicing > Configuration > Settings.

What this is not
----------------
It is not a follow-up engine: no levels, no automatic reminders, no cron. It
reads posted receivable and payable journal items and prints them.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Accounting/Accounting",
    "author": "drkds",
    "website": "https://drkdsinfo.com",
    "support": "jyotinboghani@gmail.com",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "report/drkds_statement_reports.xml",
        "report/drkds_statement_templates.xml",
        "data/mail_template_data.xml",
        "wizard/drkds_statement_wizard_views.xml",
        "views/res_partner_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "images": [],
    "installable": True,
    "application": False,
    "auto_install": False,
}
