# Branches (Lite) — user manual

## 1. Create your branches

Settings → Technical → Branches → New.

- **Name** — what staff call it: "Bengaluru Showroom".
- **Code** — short, up to eight characters: `BLR`. It is upper-cased on save
  and must be unique in the company. If you switch on branch-wise numbering it
  appears inside invoice numbers, so keep it short and never change it after
  the first invoice.
- **Address, phone, email, manager** — informational. The manager field grants
  no access on its own.
- **Archive** a branch that closes. Its past documents keep the branch and stay
  readable; it stops being offered on new ones.

Only users in the **Manage Branches** group (implied by Settings access) can
create or edit branches. Everyone else can read them, which is what the branch
field on documents needs.

## 2. Assign branches to users

Settings → Users → pick a user → **Preferences** tab.

- **Default Branch** — goes onto every sales order, invoice and contact this
  user creates.
- **Allowed Branches** — the branches this user may see and use.

Three shapes cover almost everyone:

| Who | Default Branch | Allowed Branches | Result |
| --- | --- | --- | --- |
| Counter staff | Bengaluru | Bengaluru | Sees only Bengaluru; never picks a branch |
| Area manager | Bengaluru | Bengaluru, Mysuru | Sees both; defaults to Bengaluru |
| Owner, accountant | *(blank)* | *(blank)* | Sees everything, picks a branch when needed |

The default branch must be one of the allowed branches; Odoo refuses the save
otherwise. If Allowed Branches is left empty, the default branch still applies
and the user stays unrestricted.

## 3. Day to day

The **Branch** field appears:

- on a contact, next to the salesperson;
- on a sales order, next to the salesperson — locked once the order is
  confirmed;
- on an invoice or bill, next to the journal — locked once it is posted.

It is filled in already for anyone with a default branch.

Confirming a sales order and invoicing it carries the branch onto the invoice.

## 4. Reading the numbers per branch

On the Contacts, Sales Orders and Invoices lists:

- type a branch name into the search box and pick **Branch**, or
- open **Group By → Branch**.

Group By → Branch on the Invoices list, with the *Posted* filter on, gives you
turnover per branch straight from the list totals. Add a second group-by, say
Invoice Date, for a month-by-branch grid.

## 5. Branch-wise invoice numbering (optional)

Accounting → Configuration → Settings → Customer Invoices → **Branch-wise
Invoice Numbering**.

With it on, the branch code is inserted next to the journal code:

```
INV-BLR/2026/00001      INV-MUM/2026/00001
INV-BLR/2026/00002      INV-MUM/2026/00002
```

Each branch counts on its own inside the same journal. Invoices with no branch
keep the plain `INV/2026/…` series.

This is built on Odoo's own invoice sequence mechanism, not a separate
`ir.sequence`, so the gap-detection warning and the resequencing wizard keep
working unchanged.

**Switch it on before the first invoice of a period.** Turning it on or off
mid-series leaves a visible break in the numbers that an auditor will ask
about. Do not edit a branch code once it has been used in an invoice number.

## 6. Who sees what

- A user with **Allowed Branches** filled in sees sales orders and journal
  entries of those branches, plus any document that has **no branch**.
- A user with **Allowed Branches empty** sees everything. This is the
  documented behaviour, not an oversight: owners and accountants need the whole
  picture, and an accidentally blinded accountant is a worse failure than an
  over-wide view. To restrict someone, give them branches.
- **Contacts are never hidden** by branch. The branch on a contact is a label
  for filtering and reporting.
- The Odoo administrator bypasses record rules, as always.

## 7. What this module does not do

Branch on stock transfers and payments, branch-wise access on every model, and
consolidated cross-branch reporting are not part of it.

The drkds Branch Operations app extends branches to purchases, transfers and
payments, with branch-wise access across the suite and consolidated reporting.

Part of the drkds Indian SME suite for Odoo 19 Community.
