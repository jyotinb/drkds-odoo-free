{
    "name": "Indian Payroll Components (PF, ESI, Professional Tax)",
    "summary": "Statutory Indian payroll contributions on employee contracts, with a monthly computation sheet",
    "description": """
Indian Payroll Components (PF, ESI, Professional Tax)
=====================================================

Works out the three statutory deductions every Indian employer has to get
right - Provident Fund, ESI and professional tax - from the data already on
the employee's contract, and keeps the month's working as a record that can be
reviewed later.

What it does
------------
* **Provident Fund** - employee share, employer share, the statutory wage
  ceiling, and the split of the employer share between the pension scheme and
  the PF account. A per-contract switch contributes on actual wages above the
  ceiling where the employer has agreed to.
* **ESI** - employee and employer share on gross wages, with the coverage
  threshold. An employee who crosses the threshold part way through a
  contribution period stays covered until that period ends, which is the rule
  most spreadsheets get wrong.
* **Professional tax** - a state levy, so it is modelled as a state-wise slab
  table: state, wage band, monthly tax, and the special-month amount used by
  states such as Maharashtra and Karnataka to reach the annual cap.
* **Contract fields** - PF account number, UAN, ESI number, a switch per
  component and the state whose professional tax schedule applies.
* **Monthly sheet** - pick a month and a set of employees, press Compute, and
  every component is worked out per employee with a line, a per-component
  total and a grand total. Confirm the sheet to keep it as reviewed.
* **Everything is data** - every rate, ceiling, threshold and slab is an
  editable record carrying its own effective-from date. Nothing is hardcoded,
  so a change of rate is a change of data.

What it does not do
-------------------
It does not generate payslips, it does not post journal entries and it makes
no call to any government portal. It is a computation and review working
paper, and it is deliberately nothing more.

About the numbers
-----------------
The module ships starting rates checked on 15 September 2026 - PF at 12% both
sides on a wage ceiling of INR 15,000 with 8.33% to the pension scheme, ESI at
0.75% and 3.25% on a threshold of INR 21,000, and professional tax slabs for
Maharashtra, Karnataka, West Bengal, Gujarat and Telangana only. Sources are
cited in the data file header. These figures change, states revise their
schedules, and several states levy professional tax through local bodies in
ways this table does not model. Review every number with your payroll adviser
and extend the slab table to the states you operate in before relying on a
computed sheet.

No Aadhaar number is stored anywhere by this module.

This module is a tool to assist with compliance workflows. Responsibility for
statutory compliance rests with the user and their tax professional.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Human Resources/Payroll",
    "author": "drkds",
    "website": "https://drkdsinfo.com",
    "support": "jyotinboghani@gmail.com",
    "license": "LGPL-3",
    "depends": ["hr"],
    "data": [
        "security/ir.model.access.csv",
        "data/drkds_in_payroll_components_data.xml",
        "views/drkds_in_config_views.xml",
        "views/drkds_in_payroll_sheet_views.xml",
        "views/hr_employee_views.xml",
    ],
    "images": ["static/description/cover.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
