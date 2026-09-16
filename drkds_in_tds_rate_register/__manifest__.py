{
    "name": "India TDS: Automatic Rate and Deduction Register",
    "summary": "Picks the right TDS rate from the vendor's PAN status and gives you a line level deduction register",
    "description": """
India TDS: Automatic Rate and Deduction Register
================================================

An add-on to the TDS support that is already built into Odoo, not a
replacement for it.

What comes from Odoo, not from this module
------------------------------------------
The Indian localisation (``l10n_in``, shipped with Odoo Community) already
provides all of the following, and this module changes none of it:

* the TDS **sections**, as ``l10n_in.section.alert`` records, with their per
  transaction and aggregate **thresholds** and aggregation period;
* the **rates**, as taxes tagged with a section, including the twenty per cent
  variants used when a payee has no PAN;
* the **threshold alert** on a vendor bill, worked out per PAN entity across
  the financial year;
* the **withholding entry** itself, created by the TDS wizard from a posted
  bill or payment, on the untaxed base; and
* the **TDS tax report** by section.

If you want TDS in Odoo, that is where it comes from. Install the localisation
and switch on the TDS feature in Accounting settings.

What this module adds
---------------------
* **The rate is chosen for you.** Odoo's wizard guesses the rate from the last
  withhold posted for the same PAN, account and section, and where the vendor
  has no PAN it prints a sentence asking you to remember the higher rate. Map
  a section once to its normal rate and its rate without PAN, and the wizard
  selects the right one by itself, including the section 206AA rate for a
  vendor with no PAN entity.
* **Your explicit choices are respected.** A PAN entity marked for lower
  deduction gets the lower rate you set up, or nothing at all if you set none,
  rather than being quietly charged the normal rate over a section 197
  certificate. A PAN entity marked for no deduction is left alone.
* **Odoo's own guess is left alone.** For an unremarkable vendor whose section
  the localisation already recognises from an earlier withhold, its answer
  stands. The rate stays editable in the wizard, so you always have the last
  word, and a line of text says why the rate was proposed.
* **A deduction register.** One row per deduction - vendor, PAN, section,
  base, rate, amount, bill and date - filtered and grouped by section, vendor,
  quarter and financial year, with the standard list export to XLSX or CSV.
  This is the working paper Form 26Q preparation is built from, and the tax
  report does not give it to you.
* **A year to date view.** What each vendor has been billed under each section
  since 1 April, against the section's annual threshold, beside what has
  actually been deducted. Odoo computes this figure privately, one bill at a
  time, to decide whether to warn you; here you can open it, sort it and act
  on it before the quarter closes.

Both reports are database views over the localisation's own records, so they
cannot drift away from the entries they report.

Requirements
------------
* The Indian localisation, ``l10n_in``, which this module depends on.
* **The Indian chart of accounts.** The TDS rate taxes are part of that chart
  template. On any other chart of accounts those taxes do not exist, so there
  is nothing for the rate map to point at and this module has nothing to do.
* The TDS feature switched on for the company, in Accounting settings.
* A section set on the expense accounts you want tracked, which is how the
  localisation decides a bill is in scope.

This module is a tool to assist with compliance workflows. Responsibility for
statutory compliance rests with the user and their tax professional.

The drkds Accounting India app adds Form 26Q preparation, challan tracking and
GSTR reconciliation.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Accounting/Localizations",
    "author": "drkds",
    "website": "https://drkdsinfo.com",
    "support": "jyotinboghani@gmail.com",
    "license": "LGPL-3",
    "depends": ["l10n_in"],
    "data": [
        "security/ir.model.access.csv",
        "views/drkds_tds_rate_map_views.xml",
        "views/drkds_tds_register_views.xml",
        "views/drkds_tds_ytd_views.xml",
        "views/l10n_in_withhold_wizard_views.xml",
        "views/drkds_tds_menus.xml",
    ],
    "images": [
        "static/description/cover.png",
        "static/description/screenshot_01.png",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
