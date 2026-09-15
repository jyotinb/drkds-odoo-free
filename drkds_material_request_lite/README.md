# Material Request (Lite)

Let employees request materials from stock and approve them, on Odoo 19
Community.

## Why

Odoo 19 Community moves goods between locations perfectly well. What it has no
document for is the step before that: an employee asking for material, and
somebody deciding whether they get it. `purchase_requisition` covers vendor
agreements and calls for tenders, which is a different question. This module
adds the missing internal document and nothing else.

## What it does

- **A numbered request** — sequence reference, requester, department, request
  date, required-by date, warehouse, source and destination location, reason,
  and a status.
- **Lines that keep three quantities apart** — requested, fulfilled and
  outstanding. The fulfilled figure is read back from the stock moves, never
  typed in, so the request and the warehouse cannot disagree.
- **On-hand at the source location** — every line shows the real quantity
  available where the material would come from, converted into the line's own
  unit of measure, so the approver decides on facts.
- **Submit, approve, refuse** — a single approver group and a single decision.
  A refusal must carry a reason. The state machine refuses any transition it
  does not define, and nobody can approve a request they raised themselves.
- **Fulfilment as an ordinary internal transfer** — approving creates the
  transfer for the outstanding lines and links each move back to its line.
  Validate it and the request updates itself; partial delivery leaves the
  request open and a further transfer can be raised for the remainder.
- **Closes itself** — once every line is delivered in full, the request moves
  to Done.

## Views

List, Kanban grouped by status, form, and a search view with **My Requests**,
**Awaiting My Approval** and **Outstanding** filters, plus group-by status,
requester, department, warehouse and date.

## Security

Two groups. A **Requester** raises requests and sees only their own. An
**Approver** sees every request and is the only one who can approve or refuse.

## Not included

One approval step, and it stays one step. No configurable approval engine, no
purchase fallback for shortfalls, no budget check. Keeping it legible is the
point of the lite module.

The drkds Material Request app adds purchase fulfilment for shortfalls,
multi-step approvals and budget checks.

## Install

Depends on `stock` and `hr` only, both Odoo 19 Community.

Part of the drkds Indian SME suite for Odoo 19 Community.
