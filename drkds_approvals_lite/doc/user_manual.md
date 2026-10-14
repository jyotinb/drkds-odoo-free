# Approval Requests (Lite) — user manual

## 1. Give people access

In **Settings > Users**, open a user and set the **Approval Requests** level:

- **User** — can raise requests, and can decide on the requests of the
  categories where they are listed as an approver.
- **Administrator** — sees every request, can decide on any request they
  did not ask for or raise, and maintains the categories.

The user who installed the module is an administrator already. Only users
with one of these levels can be picked as a requester or as an approver.

### Who sees what

| User | Sees |
|---|---|
| Requester | the requests they asked for, and those they raised for someone else |
| Approver | the submitted, approved, refused and cancelled requests of their categories, and every request they decided |
| Administrator | everything |

A draft stays with whoever is writing it: approvers meet a request when it
is submitted.

## 2. Set up the categories

**Approval Requests > Configuration > Categories** lists the three categories that
come installed:

| Category | Must carry |
|---|---|
| Expense claim | description, amount |
| Leave of absence (informal) | description |
| Purchase need | description, amount, contact |

Open each one and add **Approvers**. Any one of them may decide on a request
of the category. A category with no approver refuses submission, so do this
before anyone raises a request.

Changing the approvers reaches the requests already waiting for a decision:
a removed approver's to-do disappears and a new approver gets one.

The three **A request must carry** boxes decide what is checked on submit.
Add, rename or archive categories freely; the **Requests** button on the form
shows how many requests the category has had.

## 3. Raise a request

**Approval Requests > Requests > New**.

- **Title** — one line saying what is asked for.
- **Category** — picks the approvers and the rules.
- **Requester** — defaults to you. Pick someone else to ask on their
  behalf; you both see the request, they get the decision mail, and neither
  of you can decide on it.
- **Request Date**, **Amount**, **Contact** — as the category needs.
- **Description** — the case for it, on the Description tab.

Save, and the reference (`APR/00001`, `APR/00002`, ...) is allocated. The
reference never changes, even if the request is reset and resubmitted.

Click **Submit**. If the category requires something that is missing, the
submit is refused with a message naming it (a description must hold text;
an emptied editor does not count). Otherwise the request moves to
*Submitted* and each approver who can decide gets a to-do activity on it.
An approver who is the requester or raised the request, who lacks the
Approval Requests access, or who has no access to the request's company is
skipped; if nobody is left, the submit is refused.

From then on the request's content is frozen: title, category, requester,
date, amount, currency, contact, description and company can only change in
draft. The chatter stays open for messages and attachments.

Until it is decided, you or an administrator may **Cancel** it.

## 4. Decide

Approvers open **Approval Requests > To Approve**, which lists the submitted
requests in their categories, excluding their own. From the request form:

- **Approve** — records you and the time, removes the other approvers'
  to-dos and emails the requester.
- **Refuse** — opens a small window asking for the reason. The reason is
  required; it is kept on the request, shown in a red box on the form and
  emailed to the requester.

You cannot decide on a request you asked for, or raised for someone else.
Ask another approver.

The first decision is final: once approved or refused, the request is read
only and the other approvers find nothing left to do.

## 5. After a refusal or a cancellation

The requester, whoever raised the request for them, or an administrator may
click **Reset to Draft**, correct the request and submit it again. The
previous decision, decider and reason are cleared; the chatter keeps the
history.

## 6. Find things

| Filter | Shows |
|---|---|
| My Requests | requests you raised |
| To Approve by Me | submitted requests of your categories, not ones you asked for or raised |
| Decided by Me | requests you approved or refused |
| Open | draft and submitted |
| Draft / Submitted / Approved / Refused / Cancelled | that state |
| This Month | request date in the current month |

Group by state, category, requester, decided by, or request month. The list
view totals the amount column. The Kanban board shows one column per state,
in workflow order (Draft, Submitted, Approved, Refused, Cancelled), empty
columns included.

## 7. Mail templates

Two templates, **Approval Request: Approved** and **Approval Request:
Refused**, live under **Settings > Technical > Email Templates** (developer
mode). Edit the wording as you like; both are posted in the request's chatter
and sent to the requester alone, by email or in Odoo as the requester
prefers. The refused mail states the reason in full, in the mail and in the
chatter. If you edit it, keep the reason out of a quotation block: Odoo
treats a quotation as quoted text and folds it away in the chatter.

Nobody else is notified: not the request's contact (a supplier, say), and
not the other approvers, who follow the request through their to-do and
read the decision in its chatter. Keep **Default Recipients** switched off
on both templates: switched on, Odoo sends to the record's contact instead
of the requester.

## 8. Limits of the lite edition

One level of approval; the first approver to act decides. No chains, no
amount thresholds, no delegation. For those, the drkds Approvals app.

Part of the drkds Indian SME suite for Odoo 19 Community.
