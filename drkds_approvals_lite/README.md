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
| Activities | A to-do on submit for every approver who can decide, cleared on decision or cancel, moved when the category's approvers change |
| Mail | Two editable templates, sent to the requester alone on approve and on refuse |
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
   maintain categories. Only users with this access can be picked as a
   requester or an approver.
2. **Approvals > Configuration > Categories**: open each category and add
   its approvers. A request cannot be submitted in a category with no
   approver. Tick the requirements a request must meet.
3. Optionally edit the two mail templates under **Settings > Technical >
   Email Templates** (developer mode). They are addressed to the requester;
   leave *Default Recipients* off, or Odoo mails the request's contact
   instead.

## Use

1. **Approvals > Requests > New**: title, category, amount, contact,
   description. The reference is allocated on save. To ask on someone
   else's behalf, change the **Requester**.
2. **Submit**. The category's requirements are checked and every approver
   who can decide gets a to-do activity.
3. An approver opens **Approvals > To Approve** and clicks **Approve**, or
   **Refuse** and types the reason. The request records who decided and when,
   the other approvers' to-dos disappear, and the requester gets the mail.
4. A refused or cancelled request can be **Reset to Draft**, corrected and
   submitted again under the same reference.

## Behaviour worth knowing

- Nobody can decide on a request they asked for, or raised for someone
  else, even as an approver or an administrator. Someone else must do it.
- Any one approver decides; the first decision is final unless the request is
  reset to draft.
- A refusal without a reason is rejected. A required description must hold
  text; an emptied editor does not count.
- Once submitted, a request's title, category, requester, date, amount,
  currency, contact, description and company are frozen. The state and the
  decision change only through the buttons, in the API and in imports too.
  The chatter and attachments stay open.
- The requester, whoever raised the request for them, or an administrator
  can submit, cancel and reset it. An administrator can delete a draft or
  cancelled request; nothing else is deleted.
- To-dos go only to approvers who can act: not the requester or whoever
  raised the request, holding the *Approval Requests* access and access to
  the request's company. If nobody is left, submit is refused. Adding or
  removing an approver moves the to-dos of the requests already waiting.
- The decision mail goes to the requester alone. The request's contact is
  never mailed, and the other approvers, who follow the request through
  their to-do, read the decision in the chatter.
- A user sees the requests they asked for or raised, the submitted (and
  decided) requests of the categories they approve, and the requests they
  decided. A draft stays with whoever is writing it. An administrator sees
  all.

## Not in this module

One approval level only. There is no chain of approvers, no routing by
amount, no delegation and no reporting beyond the list and Kanban.

The drkds Approvals app adds multi-level and sequential approval chains,
amount-based routing, delegation and approval reporting.

Part of the drkds Indian SME suite for Odoo 19 Community.
