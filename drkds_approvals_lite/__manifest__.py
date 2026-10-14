{
    "name": "Approval Requests (Lite)",
    "summary": "One-level approval requests with categories, approvers and a decision trail, on Odoo 19 Community",
    "description": """
Approval Requests (Lite)
========================

A plain approval workflow for Odoo 19 Community. Someone needs a yes or a no
on an expense, an absence, a purchase. They raise a numbered request in a
category, the approvers of that category get an activity, one of them
approves or refuses, and the requester is told by email. The whole thing is
on the record, with chatter and tracking.

What it gives you
-----------------
* **Categories** - each with its own approvers and its own rules on what a
  request must carry: a description, an amount, a contact. Three ship ready
  to use: Expense claim, Leave of absence, Purchase need.
* **Numbered requests** - every request takes a reference such as
  ``APR/00001`` from a sequence, with title, date, amount and currency,
  contact and a rich-text description.
* **One level, any approver** - any approver of the category may decide; the
  first decision closes the request. Nobody can decide on a request they
  asked for or raised for someone else, and a refusal always carries a
  reason. Once submitted, what was asked for is frozen.
* **Activities and mail** - submitting schedules a to-do for every approver
  who can decide, and changing a category's approvers moves the to-dos of
  waiting requests; a decision clears those activities and emails the
  requester alone with the outcome, using templates you can edit.
* **Kanban, list and form** - a Kanban by state, a list, and a form with a
  status bar, Submit, Approve, Refuse, Cancel and Reset buttons.
* **Search** - my requests, to approve by me, each state, group by category,
  requester, approver, state and month.

Security
--------
An approval user sees the requests they asked for or raised, the submitted
requests of the categories they approve, and the requests they decided; a
draft stays with whoever is writing it. An approval manager sees everything
and maintains the categories. The state and the decision change only
through the buttons, in the API as well.

The paid drkds Approval Workflows app adds multi-step approval chains with amount routing, N-of-M sign-off, delegation, reminders and approval of purchase and sales orders before confirmation.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "author": "drkds",
    "website": "https://drkdsinfo.com",
    "support": "jyotin@drkdsinfo.com",
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "data": [
        "security/drkds_approvals_groups.xml",
        "security/ir.model.access.csv",
        "security/drkds_approvals_rules.xml",
        "data/drkds_approval_sequence.xml",
        "data/drkds_approval_category_data.xml",
        "data/drkds_approval_mail_templates.xml",
        "wizard/drkds_approval_refuse_wizard_views.xml",
        "views/drkds_approval_category_views.xml",
        "views/drkds_approval_request_views.xml",
        "views/drkds_approvals_menus.xml",
    ],
    "images": [
        "static/description/screenshot_01.png",
        "static/description/screenshot_02.png",
        "static/description/screenshot_03.png",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
