# drkds Free Odoo Apps — Indian SME utilities

Free, open source modules for **Odoo 19 Community Edition**, built for Indian
small and medium businesses. Every module in this repository is **LGPL-3**.

This is the free companion to the paid drkds Indian SME suite. The modules here
stand on their own: each one solves a real problem end to end rather than acting
as a trial of something else.

## Repository layout

- Branch name is the Odoo version (`19.0`). The Odoo Apps Store scans this branch.
- Each top-level folder is one installable module.
- `CLAUDE.md` holds the development rules. Read it before contributing.
- `tools/` holds the generators that keep icons and store descriptions consistent.

## Modules

### India

| Module | What it does | Depends on |
|---|---|---|
| [`drkds_in_fy_sequence`](drkds_in_fy_sequence/)<br>**Indian Financial Year Numbering** | Number invoices as INV/2026-27/0001 and reset the counter every 1 April | `base` |
| [`drkds_in_gst_summary`](drkds_in_gst_summary/)<br>**GST Outward and Inward Summary (India)** | A period GST summary by rate, by state and by HSN, for checking before you file | `l10n_in` |
| [`drkds_in_inr_words`](drkds_in_inr_words/)<br>**Rupee Amounts in Words (Lakh and Crore)** | Make Odoo's amount in words read rupees in lakh and crore, whatever language the user runs | `account` |
| [`drkds_in_msme_vendor`](drkds_in_msme_vendor/)<br>**MSME Vendor Payment Tracking (India)** | Flag micro and small vendors, watch the 45 day payment clock and list what is overdue | `account` |
| [`drkds_in_partner_validate`](drkds_in_partner_validate/)<br>**India Partner Identifier Validation** | GSTIN check digit, state and PAN cross-checks on contacts, beyond the structure check Odoo already does | `base_vat` |
| [`drkds_in_payroll_components`](drkds_in_payroll_components/)<br>**Indian Payroll Components (PF, ESI, Professional Tax)** | Statutory Indian payroll contributions on employee contracts, with a monthly computation sheet | `hr` |
| [`drkds_in_tds_rate_register`](drkds_in_tds_rate_register/)<br>**India TDS: Automatic Rate and Deduction Register** | Picks the right TDS rate from the vendor's PAN status and gives you a line level deduction register | `l10n_in` |
| [`drkds_in_upi_qr_invoice`](drkds_in_upi_qr_invoice/)<br>**UPI Payment QR on Invoices (India)** | Print a scannable UPI QR code on the customer invoice, pre-filled with the amount due | `account` |

### General and lite apps

| Module | What it does | Depends on |
|---|---|---|
| [`drkds_asset_register_lite`](drkds_asset_register_lite/)<br>**Fixed Asset Register (Lite)** | A fixed asset register with a straight line depreciation schedule, without posting entries | `base, mail` |
| [`drkds_branch_lite`](drkds_branch_lite/)<br>**Branches (Lite)** | Tag sales, invoices and contacts with a branch and report by it, inside one company | `sale, account` |
| [`drkds_budget_lite`](drkds_budget_lite/)<br>**Account Budgets (Lite)** | Set a budget per account and period, then track committed and actual spend against it | `account` |
| [`drkds_knowledge_base_lite`](drkds_knowledge_base_lite/)<br>**Knowledge Base (Lite)** | Internal articles in a section tree, with rich text, tags and search, on Odoo 19 Community | `mail` |
| [`drkds_material_request_lite`](drkds_material_request_lite/)<br>**Material Request (Lite)** | Let employees request materials from stock and approve them, on Odoo 19 Community | `stock, hr` |
| [`drkds_password_vault_lite`](drkds_password_vault_lite/)<br>**Password Vault (Lite)** | A personal encrypted vault for credentials, inside your own Odoo database | `base` |
| [`drkds_proforma_invoice`](drkds_proforma_invoice/)<br>**Proforma Invoice** | Issue a numbered proforma invoice from a quotation or a draft invoice, without touching your accounts | `sale` |
| [`drkds_ticketing_lite`](drkds_ticketing_lite/)<br>**Support Tickets (Lite)** | Customer support tickets with teams, stages and assignment, on Odoo 19 Community | `base, mail` |

Each module has its own `README.md` and a user manual under `doc/user_manual.md`.

## How these modules relate to Odoo core

Odoo 19 Community already ships a substantial Indian localisation: `l10n_in`
plus e-invoicing, e-way bills, POS, sales and stock, all free and LGPL-3.
Nothing here duplicates it. Where Odoo already does the job, these modules
either build on top of it or do not exist.

Four proposed modules were dropped during development for exactly that reason,
after the feature turned out to be in core:

| Dropped | Because core already does it |
|---|---|
| Indian number format | `res.lang` offers Indian Grouping, and base ships `en_IN` |
| Bill of Supply | `l10n_in` classifies and titles the document automatically |
| E-way bill register | `l10n_in_ewaybill` generates through the government channel |
| Menu visibility | Settings, Technical, Menu Items already edits menu groups |

Several surviving modules were narrowed for the same reason, and their
descriptions say plainly which part is Odoo's work and which is ours.

## Installing

1. Install Odoo 19 Community, from source or Docker.
2. Add this repository folder to `addons_path` in your `odoo.conf`.
3. Restart Odoo, update the apps list, then install the modules you want.

Modules are independently installable. None of them depends on another module in
this repository, and none depends on Odoo Enterprise.

## What these modules never do

- No outbound calls to any server we control. No telemetry, no licence checks.
- No scraping of government or third-party portals.
- No Aadhaar storage.
- No Enterprise dependencies.

## Compliance note

Modules that touch GST, TDS, e-way bills or MSME rules are tools to assist with
compliance workflows. Responsibility for statutory compliance rests with the
user and their tax professional. Statutory rates and thresholds change; review
the shipped defaults with your own advisor before relying on them.

## Licence

LGPL-3. See `LICENSE`.

Part of the drkds Indian SME suite for Odoo 19 Community.
