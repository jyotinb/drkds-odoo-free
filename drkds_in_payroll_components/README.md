# Indian Payroll Components (PF, ESI, Professional Tax)

Statutory Indian payroll contributions on employee contracts, with a monthly
computation sheet.

Works out the three statutory deductions every Indian employer has to get
right - Provident Fund, ESI and professional tax - from the data already on
the employee's contract, and keeps the month's working as a record that can be
reviewed later.

## What it does

* **Provident Fund** - employee share, employer share, the statutory wage
  ceiling, and the split of the employer share between the pension scheme and
  the PF account. A per-contract switch contributes on actual wages above the
  ceiling where the employer has agreed to.
* **ESI** - employee and employer share on gross wages, with the coverage
  threshold. An employee who crosses the threshold part way through a
  contribution period stays covered until that period ends.
* **Professional tax** - a state levy, so it is modelled as a state-wise slab
  table: state, wage band, monthly tax, and the special-month amount used by
  states such as Maharashtra and Karnataka to reach the annual cap.
* **Contract fields** - PF account number, UAN, ESI number, a switch per
  component and the state whose professional tax schedule applies.
* **Monthly sheet** - pick a month and a set of employees, press Compute.
  Every component is worked out per employee with a line, per-component totals
  and a grand total. Confirm the sheet to keep it as reviewed.

## What it does not do

It does not generate payslips, it does not post journal entries and it makes
no call to any government portal. It is a computation and review working
paper, and it is deliberately nothing more.

No Aadhaar number is stored anywhere by this module.

## Dependencies

`hr` only. In Odoo 19 the contract lives on `hr.version` inside `hr`, so no
separate contract module is needed, and no Enterprise or third-party module is
required.

## About the numbers

Starting figures were checked on 15 September 2026:

* PF - employee 12%, employer 12% of which 8.33% goes to the Employees'
  Pension Scheme, statutory wage ceiling INR 15,000 per month.
* ESI - employee 0.75%, employer 3.25% of gross wages, coverage threshold
  INR 21,000 per month, contribution periods April-September and
  October-March.
* Professional tax - slabs for Maharashtra, Karnataka, West Bengal, Gujarat
  and Telangana only.

Sources are cited in the header of
`data/drkds_in_payroll_components_data.xml`. These figures change, states
revise their schedules, and several states (Tamil Nadu among them) levy
professional tax through local bodies on a half-yearly basis in ways this
table does not model. Review every number with your payroll adviser and extend
the slab table to the states you operate in before relying on a computed
sheet.

## Installation

Copy the module into your addons path, update the apps list and install
**Indian Payroll Components**. Configuration lives under
Employees > Statutory Payroll > Rates and Slabs.

This module is a tool to assist with compliance workflows. Responsibility for
statutory compliance rests with the user and their tax professional.

The drkds payroll suite adds salary structures, payslip generation and
statutory return working papers built on top of these components.

Part of the drkds Indian SME suite for Odoo 19 Community.
