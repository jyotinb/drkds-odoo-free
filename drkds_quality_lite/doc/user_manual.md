# Quality Checks on Transfers (Lite) - User Manual

## 1. What a control point is

A control point is a standing instruction: "every time goods of this kind
move through this operation, inspect them like this". It is set up once by
an Inventory administrator under **Quality > Points**.

| Field | Meaning |
|---|---|
| Title | Short name shown on every check it raises. Unique per company. |
| Product | Match moves of exactly this product. |
| Product Category | Match moves of any product in this category or a sub-category. Ignored when a product is set. |
| Operation Types | Receipts, deliveries, internal transfers... Empty means all. |
| Type | **Pass / Fail** or **Measure**. |
| Minimum, Maximum, Unit | For a measure: the accepted range, boundaries included, and a free-text unit (mm, kg, pH). |
| Blocks Validation | On: the transfer waits for the check. Off: the check is recorded, the transfer is not held. |
| Instructions | Rich text shown to the inspector on the check. |

A point needs a product or a category. A measured point refuses a minimum
above its maximum. Archive a point to stop it raising checks without losing
its history; the **Checks** button on the point opens everything it raised.
A point that has raised checks cannot be deleted: archive it.

A check shows its point's current minimum, maximum and unit. Changing them
on the point changes what older checks display (their result stays as
decided), so create a new point when a tolerance changes and the old figures
must remain visible.

## 2. How checks appear

When a transfer is confirmed (**Mark as To Do**, or by confirming the
purchase or sale order behind it), one check is created for each stock move
that matches a point. This happens whoever confirms: a buyer without
Inventory rights confirming a purchase order raises the checks just the same,
for the Inventory team, without being made a follower of them. The check is
numbered `QC/00001`, `QC/00002`... and carries:

- the control point, its type and whether it blocks;
- the transfer, the move, the product, and an optional lot or serial;
- the status: **To Do**, **Passed** or **Failed**;
- the measure (for a measured check);
- who decided, when, a note, and the chatter.

Nothing is created twice: confirming again, or adding a move to a confirmed
transfer, only raises what is still missing. Cancelling a move removes its
To Do checks; decided ones stay.

A check belongs to its move and follows it. When stock moves goods to
another transfer (a backorder, or the new transfer made by **Split**), their
checks go with them.

## 3. Deciding a check

Open the check from **Quality > Checks** (default filter: To Do) or from the
**Quality Open** button on the transfer, which shows open / total.

- **Pass / Fail check**: press **Pass** or **Fail**.
- **Measured check**: type the value, press **Record Measure**. A value within
  the range passes; outside, it fails. The Pass and Fail buttons are not
  offered on a measured check, and Record Measure is refused on a pass/fail
  check. The measure starts at 0: pressing Record Measure without typing a
  value records 0, which passes if 0 lies within the range.
- A check is decided once. If someone else decided it in the meantime (for
  example while your form was open), your Pass, Fail or Record Measure is
  refused with a message saying who decided it.
- **Reset to To Do** reopens a decided check and clears who/when; the chatter
  keeps the change of status. Decide it again afterwards.
- Write what was found in the **Note** tab; drag a photo into the chatter.

## 4. Validating the transfer

Press **Validate** on the transfer as usual. If a blocking check on the goods
being validated is To Do or Failed, the validation is refused with a message
that lists each check by number, point and status. Non-blocking checks never
stop the transfer, whatever their state.

"The goods being validated" are the lines with a quantity (and, when you
tick lines as picked, the picked ones). A check entered by hand on the
transfer without a stock move always counts.

- **Partial receipt with a backorder**: pass the checks of what arrived and
  validate. The remaining quantity goes to the backorder with a new check to
  do, and a product that did not arrive at all goes there with its check.
  The backorder is held by those checks in turn.
- **Partial receipt without a backorder**: lines with no quantity are
  cancelled; their To Do checks are removed and decided ones kept.
- **Refused goods**: fail the check, set the line's quantity to 0 and
  validate without a backorder. The line is cancelled, the failed check stays
  as the record, and it no longer holds up the rest of the transfer.

**Validate from draft.** Validate on a draft transfer confirms it in the same
step. If a blocking point applies to it, the validation is refused straight
away with a message naming the points, and nothing is created: press
**Mark as To Do** to raise the checks, record them, then validate.

Once every blocking check on the goods being validated has passed, the
validation goes through. The checks keep their result as the inspection
record.

## 5. Finding things later

**Quality > Checks** offers filters for To Do, Passed, Failed, Blocking and
Checked by Me, a date filter on Checked On, and group-by on status, control
point, transfer, operation type, product and inspector. The Kanban view is
grouped by status. On transfers, the **Quality Checks Open** filter lists
transfers that still have something to inspect.

## 6. Access rights

| Group | Points | Checks |
|---|---|---|
| Inventory / User | read | read, create, write |
| Inventory / Administrator | create, write, delete | create, write, delete |

Points and checks belong to a company; users see those of their allowed
companies.

Users who can open transfers through another app without Inventory rights,
such as buyers (Purchase) and salespeople (Sales), see transfers without the
**Quality Open** button and the **Quality Checks Open** filter, since they
cannot open quality checks.
