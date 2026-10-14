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

### Fixed during review, before release

- The app menu was named *Approvals*, the name of an Odoo Enterprise app. It
  is now *Approval Requests*, the module's own title; the menu paths in the
  README and manual follow it.
- The sentence about the paid app now uses its real name, Approval
  Workflows, and lists only what it does.
- The decision mail went to the request's contact (`partner_id`, often a
  supplier) instead of the requester: Odoo 19 templates default to *Default
  Recipients*, which ignores `partner_to`. Both templates now switch it off,
  so a requester who never followed the request is told too.
- The decision mail also went to every follower, and every approver follows
  through their to-do, with a body addressed to the requester. It is now
  posted as a note to the requester alone.
- State and decision fields could be written directly (an RPC client could
  approve its own request, create one already approved, or pass
  `default_state`), and amount, category and the rest could change after
  approval. They now change only through the buttons, and the content only
  in draft.
- Whoever raised a request for someone else could approve it. They are now
  barred like the requester. The `create_uid` used for this cannot be forged.
- Raising a request for someone else failed with an access error for an
  approval user. The person who raised it now keeps sight of it.
- An approver who was the requester got a to-do they could not act on; a
  category whose only approver was the requester accepted submissions
  nobody could decide. To-dos now go only to approvers who can decide
  (not the requester or raiser, holding the access and the request's
  company), and submit is refused when none is left.
- Changing a category's approvers left removed approvers with to-dos on
  requests they could no longer open, and gave new approvers none. Waiting
  requests now follow the change.
- An approver removed from a category lost sight of the requests they had
  decided. The record rule now keeps them.
- Approvers could see and edit a clerk's draft before it was submitted.
  Drafts are now private to whoever raised them.
- An emptied description (`<p><br></p>`) satisfied *Description Required*.
- Anyone who could see a refused request could reset it to draft. Reset,
  like Cancel, now belongs to the requester, the raiser and administrators,
  and the form hides Submit, Cancel and Reset from everyone else.
- Requester and approver pickers now offer only users with the Approval
  Requests access.
- The reference could be rewritten through a direct write; it is now
  allocated once and never changes, as documented.
- The Kanban board listed its state columns in alphabetical order (Approved,
  Cancelled, Draft, Refused, Submitted), which reads the workflow backwards,
  and left out states without requests. It now shows every state, in
  workflow order.
- The refusal mail put its reason in a quotation block, which Odoo treats as
  quoted text: in the request's chatter the reason was folded away behind a
  "..." toggle, leaving "Reason given:" with nothing after it. The reason is
  now a plain paragraph, shown in full in the chatter and in the mail.
