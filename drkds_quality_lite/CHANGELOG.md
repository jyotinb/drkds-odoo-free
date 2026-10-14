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

Fixed during review, before release:

- A check now follows its stock move. Checks of moves sent to a backorder or
  a split-off transfer used to stay on the original transfer, so the
  backorder validated without inspection and the done original kept an open
  check.
- The validation gate only weighs the checks of the goods being validated
  (moves with a quantity, picked ones when lines are picked) plus checks
  entered on the transfer without a move. A partial receipt was refused
  because of a check on goods that had not arrived, and a failed check on a
  cancelled line blocked the rest of the transfer for good.
- Validate on a draft transfer that a blocking point applies to is refused
  before the transfer is confirmed, with a message saying to Mark as To Do
  first. The refusal used to roll back the checks it had just raised while
  naming them, and burnt their QC numbers.
- Checks are raised whoever confirms the move. A purchase user without
  Inventory rights could not confirm a purchase order for a product with a
  control point (access error on control points); that user is no longer
  made a follower of the checks.
- Buyers and salespeople can open transfers again: the quality fields, smart
  button and search filter on transfers are limited to Inventory users. The
  transfer form failed to load for them with an access error.
- Pass, Fail and Record Measure are refused on a check that is already
  decided; the result is changed through Reset to To Do. A second click used
  to overwrite the first inspector's decision silently.
- A control point that has raised checks cannot be deleted (archive it).
  Deleting it used to delete its checks with it.
- The three quality fields added to transfers are labelled Quality Checks
  (Lite), Quality Check Count (Lite) and Open Quality Checks (Lite).
  drkds_quality_control adds its own fields to transfers under the plain
  labels, so with both installed the export, filter and group-by pickers
  showed two identical entries for each and Odoo logged a duplicate-label
  warning at install.
- The checks list showed a measure of 0.00 on every pass/fail check, which
  read as a value someone had recorded. The Measure and Unit cells are now
  blank for pass/fail checks and filled for measured checks only, as on the
  form and the kanban card.
