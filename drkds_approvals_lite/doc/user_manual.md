# Approval Requests (Lite) — user manual

## 1. Give people access

In **Settings > Users**, open a user and set the **Approval Requests** level:

- **User** — can raise requests, and can decide on the requests of the
  categories where they are listed as an approver.
- **Administrator** — sees every request, can decide on any of them, and
  maintains the categories.

The user who installed the module is an administrator already.

## 2. Set up the categories

**Approvals > Configuration > Categories** lists the three categories that
come installed:

| Category | Must carry |
|---|---|
| Expense claim | description, amount |
| Leave of absence (informal) | description |
| Purchase need | description, amount, contact |

Open each one and add **Approvers**. Any one of them may decide on a request
of the category. A category with no approver refuses submission, so do this
before anyone raises a request.

The three **A request must carry** boxes decide what is checked on submit.
Add, rename or archive categories freely; the **Requests** button on the form
shows how many requests the category has had.

## 3. Raise a request

**Approvals > Requests > New**.

- **Title** — one line saying what is asked for.
- **Category** — picks the approvers and the rules.
- **Requester** — defaults to you.
- **Request Date**, **Amount**, **Contact** — as the category needs.
- **Description** — the case for it, on the Description tab.

Save, and the reference (`APR/00001`, `APR/00002`, ...) is allocated. The
reference never changes, even if the request is reset and resubmitted.

Click **Submit**. If the category requires something that is missing, the
submit is refused with a message naming it. Otherwise the request moves to
*Submitted* and each approver gets a to-do activity on it.

Until it is decided, you or an administrator may **Cancel** it.

## 4. Decide

Approvers open **Approvals > To Approve**, which lists the submitted
requests in their categories, excluding their own. From the request form:

- **Approve** — records you and the time, removes the other approvers'
  to-dos and emails the requester.
- **Refuse** — opens a small window asking for the reason. The reason is
  required; it is kept on the request, shown in a red box on the form and
  emailed to the requester.

You cannot decide on a request you raised yourself. Ask another approver.

The first decision is final: once approved or refused, the request is read
only and the other approvers find nothing left to do.

## 5. After a refusal or a cancellation

The requester may click **Reset to Draft**, correct the request and submit it
again. The previous decision, decider and reason are cleared; the chatter
keeps the history.

## 6. Find things

| Filter | Shows |
|---|---|
| My Requests | requests you raised |
| To Approve by Me | submitted requests of your categories, not your own |
| Decided by Me | requests you approved or refused |
| Open | draft and submitted |
| Draft / Submitted / Approved / Refused / Cancelled | that state |
| This Month | request date in the current month |

Group by state, category, requester, decided by, or request month. The list
view totals the amount column.

## 7. Mail templates

Two templates, **Approval Request: Approved** and **Approval Request:
Refused**, live under **Settings > Technical > Email Templates** (developer
mode). Edit the wording as you like; both are posted in the request's chatter
and sent to the requester's email address.

## 8. Limits of the lite edition

One level of approval; the first approver to act decides. No chains, no
amount thresholds, no delegation. For those, the drkds Approvals app.

Part of the drkds Indian SME suite for Odoo 19 Community.
