# India TDS: Automatic Rate and Deduction Register

Picks the right TDS rate from the vendor's PAN status and gives you a line
level deduction register.

**This is an add-on to the TDS support already built into Odoo, not a
replacement for it, and not TDS support in its own right.**

## What comes from Odoo, not from this module

The Indian localisation `l10n_in`, which ships with Odoo Community, already
provides all of the following. This module changes none of it:

* the TDS **sections**, as `l10n_in.section.alert` records, with their per
  transaction and aggregate **thresholds** and aggregation period;
* the **rates**, as taxes tagged with a section, including the twenty per cent
  variants used when a payee has no PAN;
* the **threshold alert** on a vendor bill, aggregated per PAN entity across
  the financial year;
* the **withholding entry** itself, created by Odoo's TDS wizard from a posted
  bill or payment, on the untaxed base; and
* the **TDS tax report** by section.

If you want TDS in Odoo, that is where it comes from. Install the localisation
and switch the TDS feature on in Accounting settings.

## What this module adds

* **The rate is chosen for you.** Odoo's wizard guesses the rate from the last
  withhold posted for the same PAN, account and section, and where the vendor
  has no PAN it prints a sentence asking you to remember the higher rate. Map a
  section once to its normal rate and its rate without PAN, and the wizard
  selects the right one by itself, including the section 206AA rate for a
  vendor with no PAN entity.
* **Your explicit choices are respected.** A PAN entity marked for lower
  deduction gets the lower rate you set up, or nothing at all if you set none,
  rather than being quietly charged the normal rate over a section 197
  certificate. A PAN entity marked for no deduction is left alone.
* **Odoo's own guess is left alone.** For an unremarkable vendor whose section
  the localisation already recognises from an earlier withhold, its answer
  stands. The rate stays editable, so you always have the last word, and a line
  of text says why the rate was proposed.
* **A deduction register.** One row per deduction — vendor, PAN, section, base,
  rate, amount, bill and date — grouped and filtered by section, vendor,
  quarter and financial year, with the standard list export to XLSX or CSV.
  This is the working paper Form 26Q preparation is built from, and the tax
  report does not give it to you.
* **A year to date view.** What each vendor has been billed under each section
  since 1 April, against the section's annual threshold, beside what has
  actually been deducted. Odoo computes this figure privately, one bill at a
  time, to decide whether to warn you; here you can open it and act on it.

Both reports are database views over the localisation's own records, so they
cannot drift away from the entries they report. No section, no threshold and no
rate is duplicated anywhere in this module.

## Requirements

* **`l10n_in`**, the Indian localisation, which ships with Odoo Community.
* **The Indian chart of accounts.** The TDS rate taxes are part of that chart
  template. On any other chart of accounts those taxes do not exist, so there
  is nothing for the rate map to point at and this module has nothing to do.
  Check this before installing.
* The TDS feature switched on for the company, in Accounting ▸ Configuration ▸
  Settings.
* A TDS section set on the expense accounts you want tracked, which is how the
  localisation decides a bill is in scope.

## Setup

1. Accounting ▸ Configuration ▸ Accounting ▸ **TDS Section Rates**.
2. Add a section. The rate without PAN is proposed for you — it is the steepest
   rate the localisation ships for that section, which is what section 206AA
   asks for. Choose the normal rate yourself, because a section such as 194C
   carries one rate for an individual contractor and another for a company.
3. Set a lower rate only where you hold a section 197 certificate.

The reports live under Accounting ▸ Reporting, as **TDS Deduction Register**
and **TDS Year to Date**.

This module is a tool to assist with compliance workflows. Responsibility for
statutory compliance rests with the user and their tax professional.

The drkds India accounting app adds Form 26Q preparation, challan tracking and
GSTR reconciliation.

Part of the drkds Indian SME suite for Odoo 19 Community.
