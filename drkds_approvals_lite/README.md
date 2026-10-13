# Approval Requests (Lite)

One-level approval requests with categories, approvers and a decision trail,
on Odoo 19 Community.

Someone needs a yes or a no. They raise a numbered request in a category, the
approvers of that category get a to-do, one of them approves or refuses, and
the requester is told by email. Chatter and tracking keep it on the record.

## What you get

| Piece | What it does |
|---|---|
| Category | Name, approvers, and which of description / amount / contact a request must carry before submit |
| Request | Reference `APR/00001` from a sequence, title, category, requester, date, amount and currency, contact, rich-text description, state, who decided, when, and the refusal reason |
| States | Draft, Submitted, Approved, Refused, Cancelled |
| Activities | A to-do for every approver on submit, cleared on decision or cancel |
| Mail | Two editable templates, posted to the requester on approve and on refuse |
| Views | Kanban by state, list with amount totals, form with status bar and buttons, search with filters and group-bys, a To Approve menu |
| Security | Approval user and approval administrator groups, with record rules and multi-company rules |

Three categories are installed: **Expense claim** (description and amount),
**Leave of absence (informal)** (description), **Purchase need** (description,
amount and contact). They have no approvers until you add some.

## Installation

Copy the module into your addons path, update the apps list and install
**Approval Requests (Lite)**. Depends on `base` and `mail` only. The user who
installs it is made an approval administrator.

## Configuration

1. **Settings > Users**: give each person the *Approval Requests* access
   level: *User* to raise and decide, *Administrator* to see everything and
   maintain categories.
2. **Approvals > Configuration > Categories**: open each category and add
   its approvers. A request cannot be submitted in a category with no
   approver. Tick the requirements a request must meet.
3. Optionally edit the two mail templates under **Settings > Technical >
   Email Templates** (developer mode).

## Use

1. **Approvals > Requests > New**: title, category, amount, contact,
   description. The reference is allocated on save.
2. **Submit**. The category's requirements are checked and every approver
   gets a to-do activity.
3. An approver opens **Approvals > To Approve** and clicks **Approve**, or
   **Refuse** and types the reason. The request records who decided and when,
   the other approvers' to-dos disappear, and the requester gets the mail.
4. A refused or cancelled request can be **Reset to Draft**, corrected and
   submitted again under the same reference.

## Behaviour worth knowing

- Nobody can decide on their own request, even an approver or an
  administrator. Someone else must do it.
- Any one approver decides; the first decision is final unless the request is
  reset to draft.
- A refusal without a reason is rejected.
- The requester or an administrator can cancel an open request. A submitted,
  approved or refused request cannot be deleted; cancel it first.
- A user sees the requests they raised plus the requests of the categories
  they approve. An administrator sees all.

## Not in this module

One approval level only. There is no chain of approvers, no routing by
amount, no delegation and no reporting beyond the list and Kanban.

The drkds Approvals app adds multi-level and sequential approval chains,
amount-based routing, delegation and approval reporting.

Part of the drkds Indian SME suite for Odoo 19 Community.
