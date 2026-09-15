# Support Tickets (Lite) — user manual

## 1. Set up the teams

Go to **Support > Configuration > Teams** and create one team per group of
people who answer a class of requests: Level 1 Support, Billing Queries,
Field Service.

For each team, set:

- **Members** — the users who work on the team's tickets. Membership is what
  makes those tickets visible to them.
- **Default Assignee** — optional. A ticket created for the team without an
  owner is assigned to this person, so nothing sits unowned.

## 2. Review the stages

**Support > Configuration > Stages** ships with five stages: New, In Progress,
Waiting on Customer, Solved and Cancelled. Each stage has:

- **Sequence** — the left to right order of the Kanban columns.
- **Team** — leave it empty for a stage every team shares, or pick a team to
  give that team a column of its own.
- **Folded in Kanban** — the column starts collapsed. Useful for end states.
- **Closing Stage** — a ticket arriving here is treated as closed and its
  closing date is stamped. Moving it back out clears the date again.

Rename, reorder or add stages freely; they are ordinary records.

## 3. Work the tickets

**Support > Tickets** opens the Kanban, filtered to open tickets.

- Click **New** to log a ticket: subject, customer, description. The reference
  is allocated on save and never changes.
- Drag a card between columns to change its stage.
- Use the priority stars for Low, Normal, High and Urgent, and the state dot
  for In Progress, Blocked and Ready.
- Tags are free labels; create them inline or in Configuration.
- The form's chatter records every stage, assignee, customer and priority
  change, and lets you schedule an activity or log a call.
- **Assign to Me** takes an unowned ticket. **Close** moves it to the first
  closing stage available to its team.

## 4. Find things

The search view carries the filters a desk actually uses:

| Filter | Shows |
|---|---|
| My Tickets | Tickets assigned to you |
| Unassigned | Tickets with no owner |
| My Teams | Tickets of teams you belong to |
| Open / Closed | Tickets outside / inside a closing stage |
| Urgent, High and Urgent, Low | By priority |
| Blocked | Tickets whose state dot is red |
| Opened This Month | Created since the first of the month |

Group by stage, team, assignee, priority, customer or opening month, and
combine group-bys to get a matrix in the list.

## 5. Reporting

**Support > Reporting > Ticket Analysis** opens a pivot of tickets by team and
assignee against stage, with a bar chart and a list on the same data. Change
the rows and columns from the pivot header, and export to a spreadsheet.

## 6. Access rights

Two groups, set on the user form under Support Tickets:

- **User** — reads and works on the tickets of their own teams and the tickets
  assigned to them. Cannot delete tickets or change teams and stages.
- **Manager** — sees and edits every ticket, and maintains teams, stages and
  tags.

## 7. Scope of this edition

There is no incoming mail gateway in this edition, so tickets are created in
the interface or through the API rather than by emailing an alias.

The drkds Support Desk app adds service level policies, a customer portal,
satisfaction ratings, canned replies and ticket merging.

Part of the drkds Indian SME suite for Odoo 19 Community.
