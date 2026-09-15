# Support Tickets (Lite)

Customer support tickets with teams, stages and assignment, on Odoo 19
Community.

A request becomes a numbered ticket, lands in a team, moves across a Kanban of
stages and closes with a recorded closing date. Chatter, followers and
scheduled activities are built in.

## What you get

| Piece | What it does |
|---|---|
| Ticket | Reference from a sequence, subject, description, customer, email, assignee, team, stage, priority, tags |
| Team | Members, optional default assignee, ticket counters |
| Stage | Ordered, global or team specific, with a folded flag and a closing flag |
| Views | Kanban with drag and drop, list, form with chatter, search with filters and group-bys |
| Reporting | Pivot and bar chart of tickets by team, assignee and stage |
| Security | Support user and support manager groups, with record rules |

## Behaviour worth knowing

- The ticket reference is unique and never reused; a duplicated ticket takes a
  fresh one.
- Moving a ticket into a stage flagged as closing stamps the closing date.
  Moving it back out clears the stamp, so a reopened ticket carries no stale
  date.
- Creating a ticket for a team with a default assignee fills the assignee, but
  an assignee given explicitly always wins.
- A support user reads the tickets of the teams they belong to plus the tickets
  assigned to them. A support manager reads and edits everything.

## Installation

Copy the module into your addons path, update the apps list and install
**Support Tickets (Lite)**. Depends on `base` and `mail` only.

## Not in this module

There is no incoming mail gateway, so tickets are created in the interface or
through the API.

The drkds Ticketing app adds service level policies, a customer portal,
satisfaction ratings, canned replies and ticket merging.

Part of the drkds Indian SME suite for Odoo 19 Community.
