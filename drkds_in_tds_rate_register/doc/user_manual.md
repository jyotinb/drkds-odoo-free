# User manual — India TDS: Automatic Rate and Deduction Register

## 1. What this module is, and what it is not

It is **not** TDS support. Odoo Community already has that, in the Indian
localisation `l10n_in`: the sections, their thresholds, the rate taxes, the
threshold alert on a bill, the wizard that posts the withholding entry and the
TDS tax report are all Odoo's, and this module changes none of them.

This module adds two things Odoo leaves to you:

1. **Which rate to use.** Odoo's wizard makes you pick the tax, guessing from
   the last withhold for the same PAN, account and section, and where the
   vendor has no PAN it only prints a reminder. Here the rate is selected.
2. **A register.** Odoo reports TDS totals through the tax report. It does not
   give you the line level list, or the running yearly total per vendor, that
   a Form 26Q working paper is built from.

This module is a tool to assist with compliance workflows. Responsibility for
statutory compliance rests with the user and their tax professional.

## 2. Before you install

* **`l10n_in` must be installed.** It is a dependency, so Odoo will pull it in.
* **Your company must be on the Indian chart of accounts.** This is the one
  requirement Odoo cannot enforce for you. The TDS rate taxes — 1% u/s 194C,
  20% u/s 194C and the rest — are part of the Indian chart template. On any
  other chart of accounts they simply do not exist, so there is nothing for the
  rate map to point at and this module has nothing to do. Check this first.
* **Switch the TDS feature on**: Accounting ▸ Configuration ▸ Settings, the TDS
  option. That is what activates the TDS tax group.
* **Set the withholding account and journal**, in the same settings page. The
  localisation's wizard refuses to post without them.

## 3. Tag the accounts

The localisation decides a bill is in scope from the **account**, not from the
bill. On each expense account you want tracked, set *TCS/TDS Section*:
professional fees to 194J, contractor payments to 194C, rent to 194I, and so
on. Nothing in this module changes that mechanism, and there is deliberately no
per-bill section override: fighting Odoo's account-driven assignment would only
give you two answers that disagree.

## 4. Map each section to its rates

Accounting ▸ Configuration ▸ Accounting ▸ **TDS Section Rates**.

Add one record per section you use:

| Field | Meaning |
| --- | --- |
| TDS Section | The localisation's section. Its thresholds and its alert stay where they are. |
| Normal Rate | The tax to use for a vendor who has quoted a PAN. |
| Rate without PAN | The tax to use under section 206AA. Proposed for you. |
| Lower Rate | The tax to use for a vendor holding a section 197 certificate. Optional. |

When you pick a section, the **rate without PAN is filled in automatically**:
it is the steepest rate the localisation ships for that section, which is what
section 206AA asks for — the higher of twenty per cent and the section rate.

The **normal rate is not guessed**, unless the section has exactly one other
rate. Section 194C carries one per cent for an individual or HUF contractor and
two per cent for a company, and which of those applies is a fact about your
vendors, not about the Act. Choosing for you would be guessing. Leave the field
empty for a section you have not decided about, and Odoo's own behaviour is
unchanged for it.

The **lower rate is never guessed and never substituted.** If a vendor is
marked for lower deduction and you have not set a lower rate, no rate is
proposed at all and the wizard tells you why. That is deliberate: quietly
falling back to the normal rate would deduct more than the vendor's certificate
allows.

Rates and thresholds change with almost every Finance Act. What each section's
rates and limits are is the localisation's data, not ours — but the decision of
which rate your vendors fall under is yours, and should be reviewed with your
tax professional at the start of each financial year.

## 5. Deducting on a bill

Nothing changes in how you work:

1. Post the vendor bill. Where a threshold is crossed, Odoo shows its own
   advisory — *"It's advisable to deduct TDS u/s 194C on this transaction"* —
   with a button onto the lines.
2. Open **Create TDS Entry** from the bill.
3. The base is Odoo's: the untaxed value of the lines carrying that section, so
   GST is already excluded.
4. **The rate is now filled in**, and a line under it says why:
   * *"Vendor has a PAN, so the normal rate for section 194C was used."*
   * *"Vendor has no PAN entity, or is marked for higher deduction, so the
     section 194C rate without PAN was used."*
   * *"Vendor is marked for lower deduction, so the lower rate set up for
     section 194C was used."*
   * *"Vendor is marked for lower deduction but section 194C has no lower rate
     set up, so no rate was proposed. Choose one yourself."*
5. Change the tax if you disagree. The reason line disappears when you do,
   because the rate is then yours and not ours. Post the entry.

### When this module stays quiet

* **The vendor is unremarkable and Odoo already knows the answer.** If the
  vendor has a PAN and the localisation recognised the rate from an earlier
  withhold on the same PAN, account and section, that answer stands. It is
  drawn from what you actually did last time, which is better informed than a
  default.
* **The section is not mapped.** Nothing is proposed, and the wizard behaves
  exactly as it does without this module.
* **The vendor is marked for no deduction.** No rate is proposed.
* **It is a customer invoice.** TCS is not this module's business.

### Where the PAN comes from

From the localisation's own `l10n_in.pan.entity` record on the vendor, and from
its *TDS Deduction* setting of Normal, Lower, Higher or No. A vendor with **no
PAN entity linked at all** is treated as having no PAN, which is what triggers
the higher rate. This module adds no PAN field of its own; if a vendor is being
charged the higher rate wrongly, link their PAN entity on the contact.

## 6. The deduction register

Accounting ▸ Reporting ▸ **TDS Deduction Register**.

One row per deduction posted: date, vendor, PAN, section, base, rate, TDS, and
the bill it came off. Base and TDS total per group. It opens grouped by section
and filtered to posted entries.

* **Filters**: posted, vendor without PAN, and one per quarter.
* **Group by**: section, vendor, quarter, financial year, deduction month.
* **Export**: select the rows and use the list's standard export for XLSX or
  CSV. No extra module and no extra Python package is needed, which is why
  there is no export button of our own.

The register is a database view over the localisation's withholding entries, so
it cannot disagree with them. Correct an entry and the register follows. A bill
that has no withholding entry does not appear, because nothing was deducted.

## 7. The year to date view

Accounting ▸ Reporting ▸ **TDS Year to Date**.

One row per vendor, per section, per financial year: what has been billed since
1 April, the section's annual threshold, whether it has been crossed, and what
has actually been deducted. Rows over the threshold are highlighted, and the
**Bills** button opens the bills behind any total.

This is the same aggregate the localisation computes to decide whether to warn
you on a bill. The difference is that Odoo computes it privately, one bill at a
time, so it can only ever tell you about the bill in front of you. Here you can
see which vendors are near a limit, and which crossed one on a bill that went
out without a deduction, before the quarter closes.

The year is the statutory April to March one, regardless of the company's own
fiscal year setting, and the register's quarters follow it: Q1 is April to June.

## 8. Limits worth knowing

* Both reports cover **purchase side TDS** only. TCS on sales is reported by
  the localisation's own tax report.
* The year to date view sums **posted vendor bills and refunds** booked to
  accounts carrying a section. A deduction made on a payment rather than a bill
  appears in the register but has no billed total to sit against.
* Surcharge and cess, relevant mainly under section 195, are part of whichever
  tax you select; this module does not add them.
* Nothing here files a return, produces a challan or contacts a government
  portal.

The drkds Accounting India app adds Form 26Q preparation, challan tracking and
GSTR reconciliation.
