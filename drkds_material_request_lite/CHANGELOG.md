# Changelog

## 19.0.1.0.0 - 2026-09-15

First release.

- Material request document with sequence, requester, department, request and
  required dates, warehouse, source and destination locations and a reason.
- Request lines with product, description, quantity, unit of measure,
  fulfilled quantity and outstanding quantity.
- Draft / Submitted / Approved / Refused / Done / Cancelled state machine that
  refuses undefined transitions.
- Approver group; nobody may approve their own request.
- Mandatory refusal reason, captured through a wizard.
- On-hand quantity per line, read from stock at the request's source location
  and converted into the line's unit of measure.
- Approval raises an internal transfer for the outstanding lines; validating it
  updates the request and closes it when everything is delivered.
- List, Kanban by state, form and search views with My Requests, Awaiting My
  Approval and Outstanding filters.
- Requester and Approver groups with record rules and full access rules.
