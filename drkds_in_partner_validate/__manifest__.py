{
    "name": "India Partner Identifier Validation",
    "summary": "Validate GSTIN, PAN, IFSC and PIN code on contacts, with GSTIN checksum and state cross-check",
    "description": """
India Partner Identifier Validation
===================================

Stops wrong Indian identifiers from ever reaching a contact record. Every
check runs at save time, so bad data never makes it into an invoice, a return
working paper or a payment file.

What it checks
--------------
* **GSTIN** - 15 character structure plus the official check-digit algorithm,
  so a transposed or invented number is rejected, not just a malformed one.
* **PAN** - the five letter, four digit, one letter structure, including the
  holder-type letter in position four.
* **IFSC** - eleven characters with the reserved zero in position five.
* **PIN code** - six digits, first digit never zero.
* **State cross-check** - the first two digits of the GSTIN are the state code.
  If they disagree with the state on the address, the save is refused.
* **PAN inside GSTIN** - characters three to twelve of a GSTIN are the PAN. If
  both fields are filled and disagree, the save is refused.

How it behaves
--------------
* Input is normalised: spaces, dashes and lower case are cleaned up on save.
* Blank is always allowed. Nothing here forces a partner to carry an
  identifier.
* A duplicate GSTIN or PAN across contacts raises a warning, not an error,
  because branches of one business legitimately share a PAN.
* The state code table is plain data, so a new state or union territory is a
  one line change.

This module is a tool to assist with compliance workflows. Responsibility for
statutory compliance rests with the user and their tax professional.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Accounting/Localizations",
    "author": "drkds",
    "website": "https://github.com/drkds/drkds-odoo-free",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "data/drkds_in_state_code_data.xml",
        "views/res_partner_views.xml",
        "views/drkds_in_state_code_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
