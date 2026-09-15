{
    "name": "India Partner Identifier Validation",
    "summary": "GSTIN check digit, state and PAN cross-checks on contacts, beyond the structure check Odoo already does",
    "description": """
India Partner Identifier Validation
===================================

Odoo already checks the **shape** of a GSTIN. This module checks the parts Odoo
does not: the **check digit**, the **state against the address**, and the
**PAN against the GSTIN**.

The GSTIN lives in the standard Tax ID (``vat``) field, exactly where Odoo's
own Indian localisation reads it from. No second GSTIN field is added.

Where the structure check comes from
------------------------------------
Structure validation is Odoo's own, from ``base_vat``. Its ``check_vat_in``
accepts the five real GSTIN forms - normal, composite and casual; UN and ON
body; NRI; TDS; TCS - but it is a pattern test only and never verifies the
fifteenth character. This module keeps all five forms working and adds the
missing check.

What this module adds
---------------------
* **GSTIN check digit** - the published GSTN algorithm, so a transposed or
  invented number is rejected, not merely a malformed one. The failure message
  names the character that was expected.
* **State cross-check** - the first two digits of the GSTIN are the state code.
  If they disagree with the state on the address, the save is refused.
* **PAN inside GSTIN** - characters three to twelve of a GSTIN are the PAN. If
  both are filled and disagree, the save is refused.
* **PAN** - the five letter, four digit, one letter structure, including the
  holder-type letter in position four.
* **IFSC** - eleven characters with the reserved zero in position five.
* **PIN code** - six digits, first digit never zero, on Indian addresses only.

How it behaves
--------------
* The check digit is applied only to the ordinary GSTIN form, a two digit state
  code followed by a PAN. UN/ON body, NRI, TDS and TCS numbers are accepted on
  Odoo's own pattern check, because the same check-digit convention is not
  confirmed for them and a wrong refusal is worse than a missed catch.
* Input is normalised: spaces, dashes and lower case are cleaned up on save,
  and only when the value actually looks like a GSTIN.
* Blank is always allowed. Nothing here forces a partner to carry an identifier.
* A duplicate GSTIN across contacts raises a notice, not an error.
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
    "depends": ["base_vat"],
    "data": [
        "security/ir.model.access.csv",
        "data/drkds_in_state_code_data.xml",
        "views/res_partner_views.xml",
        "views/drkds_in_state_code_views.xml",
    ],
    "images": ["static/description/cover.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
