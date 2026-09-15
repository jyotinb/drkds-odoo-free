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

See each module's own `README.md` for detail. Every module ships a user manual
under `doc/user_manual.md`.

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
