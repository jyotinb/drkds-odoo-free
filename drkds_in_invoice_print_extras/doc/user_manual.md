# User manual — Indian Invoice Print Extras

## 1. What changes after you install this

Nothing in the Print menu. There is still one invoice PDF, the standard one.
Open a customer invoice, **Print → Invoice**, and you get the same document as
before with five extra blocks on it.

It is worth being clear about what was already there before you installed
anything. With Odoo's Indian localisation (`l10n_in`) alone, the invoice PDF
already gives you the title *Tax Invoice* / *Bill of Supply*, the HSN/SAC
column, the HSN summary with the CGST/SGST, IGST and Cess split, the place of
supply, and the GSTINs of both parties. That is Odoo's work. This module adds:

1. GST state codes.
2. A full bank block with IFSC and branch.
3. A declaration.
4. A signature block.
5. A reverse charge marker.

## 2. Before you print

| Where | Field | Feeds |
|---|---|---|
| Settings → Companies → your company | State | Supplier state and its code |
| Settings → Companies → your company | *Indian GST Registered* | Whether any of the extras print at all |
| Contacts → each customer | State | Buyer / shipping state and code |
| Contacts → Configuration → Banks | Bank name, **BIC** | Branch and **IFSC** on the invoice |
| Invoice → Other Info → Recipient Bank | bank account | The bank block |
| Accounting → Configuration → Settings → Customer Invoices | Invoice Declaration | The declaration |
| Accounting → Configuration → Taxes | *Reverse charge* | The reverse charge marker |

The IFSC is the **BIC** field of the bank record. Odoo has no separate IFSC
field; for an Indian bank the BIC field is where the IFSC goes.

## 3. The state codes

Every Indian state has a two digit GST code — Gujarat is 24, Maharashtra 27.
Odoo already stores it on the state record, and the first two digits of a GSTIN
are that same code. The standard PDF prints state *names* only. After
installing, the code appears in brackets beside the supplier state, the buyer
state, the shipping state and the place of supply.

If a state has no code stored, the name prints on its own rather than an empty
bracket.

## 4. The bank block

The standard PDF mentions the bank only in passing, inside the payment terms
sentence. You now get a labelled block in the footer:

```
Bank Details
Account Holder: Acme Industries Pvt Ltd
Account Number: 500100200300
IFSC: DEMO0000123
Branch: Demo Bank, Amreli Branch
```

If the invoice has no Recipient Bank set, the company's own first bank account
is printed instead. If there is no bank account anywhere, the block is omitted
entirely rather than printing empty labels.

## 5. The declaration

Set it once at Accounting → Configuration → Settings → Customer Invoices →
**Invoice Declaration**. A standard sentence is installed by default. Clear the
field and no declaration prints.

It is a per-company setting, so a multi-company database can give each company
its own wording.

## 6. The signature block

Prints *For \<your company name\>*, blank space to sign, and *Authorised
Signatory*, on the right of the footer. There is nothing to configure.

## 7. The reverse charge marker

When a supply is under reverse charge the buyer pays the GST, not you, and the
invoice is supposed to say so. Tick **Reverse charge** on the tax (Accounting →
Configuration → Taxes). Any invoice using that tax then prints:

> **Reverse Charge:** Yes - tax payable by recipient

Invoices with no reverse charge tax print nothing, so ordinary invoices are
unaffected.

## 8. When the extras do not appear

All five blocks are hidden unless your company's fiscal country is India **and**
*Indian GST Registered* is ticked on the company. That is the same condition the
localisation itself uses to decide whether to print GST details, and it is
deliberate: a GST state code on the invoice of a business that is not registered
would be worse than printing nothing.

## 9. Troubleshooting

**No state code in the brackets** — the state record has no GST code. Check the
state under Contacts → Configuration → Localization → Federal States.

**IFSC missing from the bank block** — the bank record has no BIC.

**No extras at all** — check *Indian GST Registered* on the company.

**Reverse charge marker not showing** — the flag is on the *tax*, not the
invoice. Check the tax used on the lines.

---

This module is a tool to assist with compliance workflows. Responsibility for
statutory compliance rests with the user and their tax professional.
