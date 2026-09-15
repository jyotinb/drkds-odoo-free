# User manual - Indian Payroll Components

## 1. What this module is, and is not

It computes the three statutory Indian payroll components - Provident Fund,
ESI and professional tax - for a chosen month and a chosen set of employees,
and keeps the result as a reviewable record.

It does **not** generate payslips, it does **not** post accounting entries and
it makes **no** call to any government portal. Treat a sheet as a working
paper that feeds your existing payroll process, not as the payroll run itself.

No Aadhaar number is stored anywhere by this module. UAN, PF account numbers
and ESI numbers are employer-facing identifiers and are kept.

## 2. Before you start: check the rates

Everything the module computes with is an editable record. Nothing is
hardcoded. The module ships a starting set checked on 15 September 2026, with
the sources cited in the header of the data file, but rates, ceilings,
thresholds and state slab tables change by notification.

**Review every number with your payroll adviser before you rely on a sheet.**

Go to **Employees > Statutory Payroll > Rates and Slabs**.

### Provident Fund Rates

| Field | Shipped value | Meaning |
| --- | --- | --- |
| Employee Share (%) | 12 | Deducted from the employee on the PF wage. |
| Employer Share (%) | 12 | Total employer contribution before the split. |
| Pension Share (%) | 8.33 | Part of the employer share sent to the pension scheme. |
| Wage Ceiling | 15,000 | PF is computed on this when the wage is higher. |
| Pension Ceiling | 15,000 | The pension share is never computed on more than this. |

The employer PF share is the employer share less the pension share, so it
always adds back to the total.

### ESI Rates

| Field | Shipped value | Meaning |
| --- | --- | --- |
| Employee Share (%) | 0.75 | On the full gross wage. |
| Employer Share (%) | 3.25 | On the full gross wage. |
| Gross Wage Threshold | 21,000 | At or below this the employee is covered. |
| First Period Starts In Month | 4 | April. |
| Contribution Period Length | 6 | So the periods are April-September and October-March. |

There is no ESI ceiling. The threshold only decides *who* is covered;
contributions are then computed on the whole gross wage.

### Professional Tax Slabs

Professional tax is a **state** levy. There is no national rate, and every
state publishes its own schedule, its own exemptions and its own collection
frequency. Each row here is one wage band for one state:

* **State**, **Monthly Wage From**, **Monthly Wage To** - the band. Both
  bounds are inclusive. Leave *To* at zero for the open-ended top band.
* **Monthly Tax** - what is deducted in an ordinary month.
* **Special Month** / **Special Month Tax** - for states that collect a
  different amount in one month of the year. Maharashtra and Karnataka collect
  300 in February instead of 200, so the year reaches the 2,500 annual cap.
  Leave the special month empty where the state charges the same every month.
* **Effective From** - when a state revises its schedule, add the new rows
  with a later effective date rather than editing the old ones. Sheets for
  earlier months keep computing on the old table.

Slabs ship for **Maharashtra, Karnataka, West Bengal, Gujarat and Telangana
only**, as a starting point, and they must be verified. Every other state is
missing and will compute to zero until you add it. Some states - Tamil Nadu
for one - levy professional tax through local bodies on a half-yearly basis;
that shape is not modelled here and those states need to be handled outside
this module.

## 3. Set up the employees

Open an employee, go to the **Payroll** tab, and fill in **Indian Statutory
Components**:

* **PF Applicable** - switch on to contribute PF. Then:
  * **PF on Actual Wage** - contribute on the full wage instead of capping it
    at the statutory ceiling. Contributions above the ceiling are voluntary,
    so leave this off unless the employer has agreed to it.
  * **PF Account Number** and **UAN**.
* **ESI Applicable** - switch on to contribute ESI. Then:
  * **ESI Number**.
  * **ESI Covered Since** - the date the employee last became covered. This is
    what drives the mid-period continuation rule described below, so fill it
    in for anyone whose wage may rise past the threshold.
* **Professional Tax Applicable** - switch on to deduct professional tax. Then:
  * **Professional Tax State** - usually the state of the work location, not
    the state of residence.

A component switched off computes to zero for that employee. It is never
guessed.

## 4. The mid-period ESI rule

If an employee's gross wage rises above the threshold part way through a
contribution period, coverage does **not** stop that month. It continues until
the end of the period, then ends.

The module applies this by comparing **ESI Covered Since** with the month of
the sheet. Covered from April, raised to 26,000 in July: July, August and
September still deduct ESI on the full 26,000. From October there is no
deduction.

Leave **ESI Covered Since** empty and a wage above the threshold simply means
no deduction.

## 5. Run a monthly sheet

**Employees > Statutory Payroll > Statutory Components > New**.

1. Pick the **Month** and **Year**, and the company.
2. Pick the **Employees**. Leave the field empty to pull in every employee of
   the company that has at least one component switched on.
3. Press **Compute**. One line per employee appears with the wage, each
   component, and the line's employee and employer totals.
4. Check the figures. The footer carries the per-component totals and the
   grand total, which is the sum of the employee and employer totals.
5. Add **Review Notes** saying who checked the sheet and against what.
6. Press **Confirm** to keep the sheet as reviewed. A confirmed sheet cannot
   be recomputed; reset it to draft first if something changed.

One sheet per company per month is allowed, so a month's working paper has a
single agreed version.

## 6. What the numbers mean on a line

| Column | How it is worked out |
| --- | --- |
| Monthly Wage | The wage on the employee's current contract version. |
| PF Employee | Employee share of the PF base (capped wage, or actual wage if that switch is on). |
| PF Employer (Pension) | Pension share of the wage, capped at the pension ceiling. |
| PF Employer (Fund) | The employer share less the pension part. |
| ESI Covered | Ticked when ESI was deducted, including the mid-period continuation case. |
| ESI Employee / Employer | The rates applied to the full gross wage. |
| Professional Tax | The state slab for the wage, using the special-month amount where the month matches. |
| Total Deducted | PF employee + ESI employee + professional tax. |
| Employer Cost | PF employer (both parts) + ESI employer. Professional tax is an employee deduction, so it is not employer cost. |

## 7. Access

Reading the rates and slabs needs the HR Officer group. Creating and computing
sheets needs the HR Manager group, because the computation reads contract
wages.

---

This module is a tool to assist with compliance workflows. Responsibility for
statutory compliance rests with the user and their tax professional.
