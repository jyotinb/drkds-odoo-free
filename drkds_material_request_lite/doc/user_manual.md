# Material Request (Lite) — user manual

## 1. Set up

Install the module. It depends on **Inventory** (`stock`) and **Employees**
(`hr`), both Community.

Under *Settings → Users*, give each person one of the two roles in the
**Material Request** category:

- **Requester** — raises requests, sees only their own.
- **Approver** — sees every request, approves or refuses. Implies Requester.

Both roles also need Odoo's own **Inventory / User** access to see the transfer
that fulfils a request.

## 2. Raise a request

*Material Requests → Requests → New*.

| Field | Meaning |
| --- | --- |
| Reference | Filled automatically from the `drkds.material.request` sequence. |
| Requester | You, by default. Only editable while the request is Draft. |
| Department | Taken from your employee record; editable. |
| Request Date | Now, by default. |
| Required By | When you need it. Informative, it drives no scheduling. |
| Warehouse | Where the material comes from. |
| Source Location | The warehouse stock location by default. On-hand figures are read here. |
| Destination Location | Where the material should end up — a workshop, a site. |
| Reason | On the *Reason* tab. The approver reads it. |

Add a line per product: product, description, quantity and unit. The **On Hand**
column shows what is actually available at the source location, in the line's
unit, and turns red when it is short of what you asked for.

Press **Submit**. The request can no longer be edited by you.

## 3. Approve or refuse

*Material Requests → To Approve* opens the requests waiting on you.

- **Approve** — records who approved and when, and immediately creates an
  internal transfer holding every outstanding line. The transfer is a normal
  Odoo transfer; it appears on the *Transfers* button.
- **Refuse** — asks for a reason. The reason is mandatory and is shown to the
  requester in a red band on the request.

You cannot approve a request you raised yourself, whatever your access.

## 4. Deliver the material

Open the transfer from the *Transfers* button, reserve and validate it as you
would any internal transfer.

- Validating updates **Fulfilled** and **Outstanding** on each line.
- If you deliver less than requested, the request stays **Approved** and the
  shortfall stays outstanding. Press **New Transfer** on the request to raise
  another transfer for the remainder.
- When every line is fulfilled in full, the request closes itself and moves to
  **Done**.

## 5. Cancelling

**Cancel** on a request also cancels any transfer that is not yet done. A
cancelled or refused request can be reset to Draft and reworked.

## 6. Finding things

The search view gives you **My Requests**, **Awaiting My Approval**,
**Outstanding** and **Overdue**, and grouping by status, requester, department,
warehouse and request date. The Kanban view is grouped by status.

## 7. What this module does not do

Fulfilling a shortfall by raising a purchase order, multi-step approval chains
and budget checking are not part of the lite module.

The drkds Material Requests app adds purchase fulfilment for shortfalls,
multi-step approvals and budget checks.

Part of the drkds Indian SME suite for Odoo 19 Community.
