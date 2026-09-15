{
    "name": "Branches (Lite)",
    "summary": "Tag sales, invoices and contacts with a branch and report by it, inside one company",
    "description": """
Branches (Lite)
===============

One company, one GSTIN, several counters. This module adds a **branch** - a
plain place of business - to contacts, sales orders and invoices, defaults it
from the user, and keeps each branch inside its own documents.

Why not just use an analytic account
------------------------------------
Odoo's analytic accounting is the right tool for cost and margin analysis, and
this module does not replace it. It does not, however, do four things that a
branch needs:

* Analytic distribution lives on **lines**, as a JSON map of percentages. There
  is no single header field a counter clerk can pick, and no whole-document
  answer to "which branch was this".
* An analytic distribution model defaults from the **partner, category or
  company**, never from the **user**. Counter staff would have to choose.
* Analytic accounts do not scope **who may read a document**. There is no
  record rule keyed on the analytic distribution of a line.
* Analytic accounts have nothing to do with **document numbering**.

So: use analytic accounts for cost centres, and a branch for the place the
document was raised. They coexist.

What this module does
---------------------
* **Branch model** - name, code, address, manager, ordering and an archive
  flag, all inside one company. No second chart of accounts, no second
  currency, no inter-branch accounting.
* **Branch on the documents that matter** - contacts, sales orders and
  customer/vendor invoices. The branch on a sales order is carried onto the
  invoice it creates.
* **Defaulted from the user** - every user has one default branch and,
  optionally, a list of branches they may use. Counter staff never pick one.
* **Branch-scoped visibility** - global record rules on sales orders and
  journal entries. A user restricted to Bengaluru does not see Mumbai's
  invoices. A user with no branch assigned is unrestricted, which is what an
  owner or an accountant needs.
* **Branch-wise reporting** - a Branch filter and a Branch group-by on the
  contact, sales order and invoice lists, so any of them reads branch by
  branch without a new report.
* **Optional branch-wise invoice numbering** - one switch in Accounting
  settings turns INV/2026/00001 into INV-BLR/2026/00001, with each branch
  numbering independently. It is built on Odoo's own sequence mixin, so gap
  detection and the resequencing wizard keep working.

What it deliberately leaves alone
---------------------------------
* **Contacts are not hidden** by branch. A contact is shared master data,
  pointed at by users, companies and vendors; hiding it breaks more than it
  protects. The branch on a contact is a reporting label.
* **Stock transfers, purchases and payments** carry no branch here, and the
  dependency list stays at ``sale`` and ``account`` rather than reaching into
  every app.

The drkds Branch Operations app extends branches to purchases, transfers and
payments, with branch-wise access across the suite and consolidated reporting.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Sales/Sales",
    "author": "drkds",
    "website": "https://drkdsinfo.com",
    "license": "LGPL-3",
    "depends": ["sale", "account"],
    "data": [
        "security/drkds_branch_security.xml",
        "security/ir.model.access.csv",
        "views/drkds_branch_views.xml",
        "views/res_users_views.xml",
        "views/res_partner_views.xml",
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "images": ["static/description/cover.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
