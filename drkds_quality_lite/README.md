# Quality Checks on Transfers (Lite)

Pass/fail and measured quality checks on receipts and deliveries, on Odoo 19
Community.

## Why

Odoo 19 Community receives and ships goods, but it has no place to record
whether the goods were actually inspected before they went on the shelf or out
of the door. This module adds that one record, and the rule that goes with it:
a transfer with an open or failed blocking check cannot be validated.

## What it does

- **Control points** say what must be checked: a product, or a whole product
  category (sub-categories included), on chosen operation types or on all of
  them, with written instructions the inspector reads on the check.
- **Two kinds of check**: a plain pass/fail decision, or a measured value with
  a minimum, a maximum and a unit. A measure outside the range fails on its
  own; inside the range (boundaries included) it passes.
- **Checks are raised automatically** when a transfer is confirmed: one check
  per stock move that matches a point. Confirming again, or adding a move to
  an already confirmed transfer, raises only what is missing. A cancelled move
  drops its open checks and keeps decided ones as history.
- **The gate**: validation is refused while any blocking check on the
  transfer is still to do or has failed. The error names the checks. A point
  marked non-blocking records the result without holding up the goods.
- **Numbered records**: `QC/00001` onward, each linked to its transfer, move,
  product and optional lot, with who decided, when, a note and a chatter for
  photos and discussion.
- **Smart button on the transfer** showing open / total checks.

## Install

Depends on `stock` only. Install from Apps; no configuration step is needed.

## Configure

Quality > Points (Inventory manager rights):

1. Give the point a title and the product or product category it applies to.
2. Pick the operation types, or leave the field empty for all of them.
3. Choose **Pass / Fail** or **Measure**. For a measure, set minimum, maximum
   and unit.
4. Leave **Blocks Validation** on to hold the transfer until the check passes;
   turn it off for an advisory check.
5. Write the instructions on the Instructions tab.

## Use

1. Confirm a receipt or delivery as usual. Matching checks appear under
   Quality > Checks and on the transfer's **Quality Open** button.
2. Open a check. For pass/fail, press **Pass** or **Fail**. For a measure,
   enter the value and press **Record Measure**; the result follows the
   range. Add a note or attach a photo in the chatter.
3. Validate the transfer. If a blocking check is still open or failed, the
   validation is refused and the message lists the checks. Fix the goods or
   the record, then validate again.

## Access

| Group | Points | Checks |
|---|---|---|
| Inventory / User | read | read, create, write |
| Inventory / Administrator | full | full |

Both models carry a company and a multi-company record rule.

## Notes

- A check is decided by the user who presses the button; `Checked By` and
  `Checked On` are set then and cleared by **Reset to To Do**.
- If both a product and a category are set on a point, the product is what
  is matched; the category is ignored.
- No checks on manufacturing orders, no sampling plans, no worksheets, no
  quality alerts. The module records inspections on transfers and keeps bad
  goods from being validated, nothing more.
- No outbound calls of any kind.

Part of the drkds Indian SME suite for Odoo 19 Community.
