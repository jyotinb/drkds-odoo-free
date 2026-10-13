# Changelog

## 19.0.1.0.0 - 2026-10-13

First release.

- Control points (`drkds.quality.point`): title, product or product category,
  operation types, instructions, pass/fail or measured type with minimum,
  maximum and unit, blocking flag, active flag, company.
- Quality checks (`drkds.quality.check`): sequence `QC/00001`, point,
  transfer, move, product, lot, To Do / Passed / Failed status, measure, note,
  inspector and date, chatter for photos.
- One check per matching move raised when a transfer is confirmed; nothing
  raised twice; open checks of a cancelled move removed.
- Validation of a transfer refused while a blocking check is To Do or Failed;
  non-blocking points never hold the goods.
- Quality menu with Checks and Points; list, kanban, form and search views;
  smart button and search filter on transfers.
- Access through the Inventory User and Administrator groups, multi-company
  record rules.
- Unit tests and an end-to-end scenario (receipt of three products against
  two points).
