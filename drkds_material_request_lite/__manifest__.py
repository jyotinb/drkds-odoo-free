{
    "name": "Material Request (Lite)",
    "summary": "Let employees request materials from stock and approve them, on Odoo 19 Community",
    "description": """
Material Request (Lite)
=======================

Odoo 19 Community moves goods between locations perfectly well. What it has no
document for is the step before that: an employee asking for the material, and
somebody deciding whether they get it. ``purchase_requisition`` covers vendor
agreements and calls for tenders, which is a different question entirely.

This module adds the missing internal document and nothing else.

What it does
------------
* **A numbered request** - sequence-numbered, with requester, department, the
  date it was raised, the date it is needed by, the warehouse it should come
  from, the location it should go to, and a reason the approver can read.
* **Lines that keep three quantities apart** - what was asked for, what has
  actually been delivered, and what is still outstanding. The delivered figure
  is read back from the stock moves, never typed in.
* **On-hand quantity at the source location** - each line shows the real
  quantity available where the material would come from, converted into the
  line's own unit, so the approver decides on facts rather than a guess.
* **Submit, approve, refuse** - one approver group, one decision. A refusal
  must carry a reason; an empty one is rejected. The state machine refuses
  every transition it does not define, so a draft cannot be approved and an
  approved request cannot be quietly edited.
* **Fulfilment as an ordinary internal transfer** - approving creates the
  transfer for the outstanding lines and links each move back to its line.
  Validate the transfer and the request updates itself; a partial delivery
  leaves it open, and a further transfer can be raised for the remainder.
* **Closes itself** - once every line is delivered in full the request moves
  to Done on its own.

Who sees what
-------------
Two groups. A **Requester** raises requests and sees only their own. An
**Approver** sees every request and is the only one who can approve or refuse.
Nobody can approve a request they raised themselves.

Deliberately not included
-------------------------
The workflow is one step and stays one step. There is no configurable approval
engine, no purchase fallback for shortfalls and no budget check. Keeping it
legible is the point of the lite module.

The drkds Material Request app adds purchase fulfilment for shortfalls,
multi-step approvals and budget checks.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Inventory/Inventory",
    "author": "drkds",
    "website": "https://github.com/drkds/drkds-odoo-free",
    "license": "LGPL-3",
    "depends": ["stock", "hr"],
    "data": [
        "security/drkds_material_request_security.xml",
        "security/ir.model.access.csv",
        "data/drkds_material_request_data.xml",
        "wizard/drkds_material_request_refuse_views.xml",
        "views/drkds_material_request_views.xml",
    ],
    "images": ["static/description/cover.png"],
    "installable": True,
    "application": True,
    "auto_install": False,
}
