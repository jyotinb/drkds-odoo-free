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
  per stock move that matches a point, whoever confirms it (an Inventory
  user, or a buyer confirming a purchase order). Confirming again, or adding
  a move to an already confirmed transfer, raises only what is missing. A
  cancelled move drops its open checks and keeps decided ones as history.
- **Checks follow their moves**: when part of a transfer is validated, the
  remaining quantity goes to the backorder with a new check to do, and moves
  sent to a backorder or a split-off transfer take their checks with them.
- **The gate**: validation is refused while a blocking check on the goods
  being validated is still to do or has failed. The error names the checks.
  Goods that did not arrive (no quantity) do not hold up the rest: they go to
  the backorder with their checks, or are cancelled with them when no
  backorder is made. A point marked non-blocking records the result without
  holding up the goods.
- **Numbered records**: `QC/00001` onward, each linked to its transfer, move,
  product and optional lot, with who decided, when, a note and a chatter for
  photos and discussion.
- **Smart button on the transfer** showing open / total checks.

## Install

Depends on `stock` only. Install from Apps; no configuration step is needed.

## Configure

Quality Checks > Points (Inventory manager rights):

1. Give the point a title and the product or product category it applies to.
2. Pick the operation types, or leave the field empty for all of them.
3. Choose **Pass / Fail** or **Measure**. For a measure, set minimum, maximum
   and unit.
4. Leave **Blocks Validation** on to hold the transfer until the check passes;
   turn it off for an advisory check.
5. Write the instructions on the Instructions tab.

A point that has raised checks cannot be deleted, because its checks are the
inspection record of past transfers. Archive it instead.

## Use

1. Confirm a receipt or delivery as usual (**Mark as To Do**, or by
   confirming the purchase or sale order). Matching checks appear under
   Quality Checks > Checks and on the transfer's **Quality Open** button.
2. Open a check. For pass/fail, press **Pass** or **Fail**. For a measure,
   enter the value and press **Record Measure**; the result follows the
   range. Add a note or attach a photo in the chatter.
3. Validate the transfer. If a blocking check on the goods being validated
   is still open or failed, the validation is refused and the message lists
   the checks. Fix the goods or the record, then validate again.

**Validate** pressed on a draft transfer that a blocking point applies to is
refused with a message naming the points: press **Mark as To Do** first so
the checks are raised, record them, then validate.

## Access

| Group | Points | Checks |
|---|---|---|
| Inventory / User | read | read, create, write |
| Inventory / Administrator | full | full |

Both models carry a company and a multi-company record rule.

Users of other apps who can open transfers without Inventory rights (buyers
through Purchase, salespeople through Sales) do not see the quality button or
filter on the transfer, and can still confirm orders: the checks are raised
for the Inventory team, and those users are not made followers of them.

## Notes

- A check is decided once, by the user who presses the button; `Checked By`
  and `Checked On` are set then. A second Pass, Fail or Record Measure on a
  decided check is refused. To change a result, press **Reset to To Do**
  (recorded in the chatter, clears who and when), then decide again.
- A pass/fail check has no measure: its Measure and Unit cells in the checks
  list stay blank and its form has no Measure section. Only measured checks
  show a value.
- The measure field starts at 0. Pressing **Record Measure** without typing a
  value records 0, which passes if 0 lies within the range.
- A check shows its point's current minimum, maximum and unit. Changing them
  on the point changes what older checks display; their result stays as
  decided. Create a new point when a tolerance changes and the old figures
  must stay visible.
- If both a product and a category are set on a point, the product is what
  is matched; the category is ignored.
- No checks on manufacturing orders, no sampling plans, no worksheets, no
  quality alerts. The module records inspections on transfers and keeps bad
  goods from being validated, nothing more.
- No outbound calls of any kind.

The paid drkds Quality Control app adds sampling plans, checklists and worksheets, quarantine of failed goods, quality alerts, checks on manufacturing orders and pass-rate reporting.

Part of the drkds Indian SME suite for Odoo 19 Community.
