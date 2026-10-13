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

## 2. How checks appear

When a transfer is confirmed (Mark as Todo, or directly by Validate from
draft), one check is created for each stock move that matches a point. The
check is numbered `QC/00001`, `QC/00002`... and carries:

- the control point, its type and whether it blocks;
- the transfer, the move, the product, and an optional lot or serial;
- the status: **To Do**, **Passed** or **Failed**;
- the measure (for a measured check);
- who decided, when, a note, and the chatter.

Nothing is created twice: confirming again, or adding a move to a confirmed
transfer, only raises what is still missing. Cancelling a move removes its
To Do checks; decided ones stay.

## 3. Deciding a check

Open the check from **Quality > Checks** (default filter: To Do) or from the
**Quality Open** button on the transfer, which shows open / total.

- **Pass / Fail check**: press **Pass** or **Fail**.
- **Measured check**: type the value, press **Record Measure**. A value within
  the range passes; outside, it fails. The Pass and Fail buttons are not
  offered on a measured check, and Record Measure is refused on a pass/fail
  check.
- **Reset to To Do** reopens a decided check and clears who/when.
- Write what was found in the **Note** tab; drag a photo into the chatter.

## 4. Validating the transfer

Press **Validate** on the transfer as usual. If any blocking check on it is
To Do or Failed, the validation is refused with a message that lists each
check by number, point and status. Non-blocking checks never stop the
transfer, whatever their state.

Once every blocking check has passed, validation goes through and the
transfer is done. The checks keep their result as the inspection record.

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
