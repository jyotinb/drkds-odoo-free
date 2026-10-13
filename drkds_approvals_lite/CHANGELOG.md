# Changelog

## 19.0.1.0.0 - 2026-10-13

First release.

- Approval categories with approvers and required-field flags; three seeded:
  Expense claim, Leave of absence (informal), Purchase need.
- Approval requests with a sequence reference, title, category, requester,
  date, amount and currency, contact and description, on the mail thread and
  activity mixins with field tracking.
- Draft, submitted, approved, refused and cancelled states with Submit,
  Approve, Refuse (wizard with mandatory reason), Cancel and Reset to Draft.
- Category requirements checked on submit; self-approval refused.
- A to-do activity per approver on submit, cleared on decision or cancel.
- Mail templates posted to the requester on approve and refuse.
- Kanban, list, form, search and activity views, Requests and To Approve
  menus, category configuration menu.
- Approval user and administrator groups with record rules and multi-company
  rules.
