# Branches (Lite)

Tag sales, invoices and contacts with a branch and report by it, inside one
company.

One company, one GSTIN, several counters. This module adds a **branch** — a
plain place of business — to contacts, sales orders and invoices, defaults it
from the user, and keeps each branch inside its own documents.

## Why not just use an analytic account?

Odoo's analytic accounting is the right tool for cost and margin analysis, and
this module does not replace it. Use both. But analytic accounting does not do
four things a branch needs:

| Need | Analytic accounting | This module |
| --- | --- | --- |
| One field on the document | No — distribution is a JSON percentage map on **lines** | Yes, a header Many2one |
| Default from the **user** | No — distribution models key off partner, category or company | Yes |
| Restrict who may **read** the document | No | Yes, global record rules |
| Affect document **numbering** | No | Optional |

If what you want is cost centres, use analytic accounts and skip this module.

## What it does

- **Branch model** — name, code, address, manager, ordering, archive flag, all
  inside one company. No second chart of accounts, no inter-branch accounting.
- **Branch on contacts, sales orders and invoices.** The branch on a sales
  order is carried onto the invoice it creates.
- **Defaulted from the user.** Each user has one default branch and optionally
  a list of branches they may use. Counter staff never pick one.
- **Branch-scoped visibility** through global record rules on sales orders and
  journal entries.
- **Branch-wise reporting** — Branch filter and Branch group-by on the contact,
  sales order and invoice lists.
- **Optional branch-wise invoice numbering** — one switch in Accounting
  settings turns `INV/2026/00001` into `INV-BLR/2026/00001`, each branch
  numbering independently.

## The record rule, precisely

- A user **with** allowed branches sees documents in those branches, **plus**
  documents with no branch at all (so nothing created before install, or by a
  background job, disappears).
- A user **with no** allowed branches is **unrestricted** and sees every
  branch. That is deliberate: the owner, the accountant and the system user are
  the people with no branch, and silently blinding them is worse than showing
  too much. Restriction begins the moment you fill in Allowed Branches.
- The rules are **global**, not group rules, because `account` ships
  `account_move_see_all` with the domain `[(1, '=', 1)]` for the invoicing
  group, and Odoo ORs group rules together — a group rule here would be ORed
  away for exactly the users it is meant to restrict.
- **Contacts are not scoped.** A contact is shared master data pointed at by
  users, companies and vendors; hiding it breaks more than it protects. The
  branch on a contact is a reporting label.

## Install

Copy into your addons path, update the apps list, install **Branches (Lite)**.
Depends on `sale` and `account` only.

## Not in this module

Branch on stock transfers and payments, branch-wise access on every model, and
consolidated cross-branch reporting.

The drkds Branch Operations app extends branches to purchases, transfers and
payments, with branch-wise access across the suite and consolidated reporting.

This module can be installed alongside the paid drkds Branch Operations app:
they use separate models and keep separate data, so neither blocks the other
and no branch defined here is carried across.

Part of the drkds Indian SME suite for Odoo 19 Community.

Licence: LGPL-3.
