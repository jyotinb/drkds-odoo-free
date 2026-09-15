{
    "name": "Support Tickets (Lite)",
    "summary": "Customer support tickets with teams, stages and assignment, on Odoo 19 Community",
    "description": """
Support Tickets (Lite)
======================

A small, complete support desk for Odoo 19 Community. A customer request
becomes a numbered ticket, lands in a team, moves across a Kanban of stages
and closes with a recorded closing date. Nothing more, nothing to configure
before it is useful.

What it gives you
-----------------
* **Numbered tickets** - every ticket gets a unique reference from a sequence,
  so it can be quoted in an email or on the phone.
* **Teams** - a support team has members and an optional default assignee, so
  a new ticket is never unowned by accident.
* **Stages** - ordered, global or team specific, each with a folded flag for
  the Kanban and a closed flag that stamps the closing date.
* **Kanban, list and form** - drag a ticket between stages, or work from a
  list. The form carries chatter, followers and scheduled activities.
* **Search that answers real questions** - my tickets, unassigned, open,
  closed, urgent, late-priority, plus group by stage, team, assignee,
  priority and customer.
* **Reporting** - a pivot and a grouped list of tickets by stage, team and
  assignee, built on the ticket model itself rather than a custom SQL view.

Security
--------
Two groups. A support user works with the tickets of the teams they belong to
and the tickets assigned to them. A support manager sees and edits everything
and maintains teams and stages.

The drkds Ticketing app adds service level policies, a customer portal,
satisfaction ratings, canned replies and ticket merging.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Services",
    "author": "drkds",
    "website": "https://github.com/drkds/drkds-odoo-free",
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "data": [
        "security/drkds_ticketing_groups.xml",
        "security/ir.model.access.csv",
        "security/drkds_ticketing_rules.xml",
        "data/drkds_ticket_sequence.xml",
        "data/drkds_ticket_stage_data.xml",
        "views/drkds_ticket_stage_views.xml",
        "views/drkds_ticket_team_views.xml",
        "views/drkds_ticket_views.xml",
        "report/drkds_ticket_report_views.xml",
        "views/drkds_ticketing_menus.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
