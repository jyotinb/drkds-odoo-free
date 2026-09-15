# UPI Payment QR on Invoices (India)

Print a scannable UPI QR code on the customer invoice, pre-filled with the
amount due.

Your customer opens the invoice PDF or the portal page, scans the code with
any UPI application, and the payee, the amount and the invoice reference are
already filled in. Nothing is typed, so nothing is mistyped, and the credit
that reaches your bank carries the invoice number you need to match it.

An existing free module covers UPI on the point of sale screen. This one is
for the invoice document and the customer portal.

## Features

- QR code on the invoice PDF, beside the payment block, with the UPI ID
  printed underneath.
- The same QR code on the customer portal invoice page.
- Amount taken from the residual, so a partly paid invoice asks for the
  balance.
- Invoice reference carried as the UPI transaction note and transaction
  reference.
- UPI ID validated on save against the `name@handle` shape. Blank is allowed
  and simply prints no code.
- Never printed on a vendor bill, a credit note, a draft or a paid invoice.

## Configuration

Settings > Accounting > Customer Payments > **UPI Payment QR (India)**:

| Setting | Meaning |
| --- | --- |
| UPI ID (VPA) | The address money is sent to, for example `acme@okhdfcbank`. Empty means no QR code. |
| Payee Name | Shown in the payer's UPI app. Falls back to the company name. |
| Pre-fill the amount due | Embed `am`. Off gives an open code the customer types an amount into. |
| Include the invoice reference | Embed `tn` and `tr`. |

## How the link is built

Per the NPCI UPI Linking Specifications for deep linking:

```
upi://pay?pa=<vpa>&pn=<payee>&am=<amount>&cu=INR&tn=<note>&tr=<reference>
```

Every value is percent-encoded. The QR image is rendered with Odoo's own
`ir.actions.report.barcode` helper, the same one behind
`/report/barcode/QR/...`, so the module bundles no QR library and adds no pip
dependency.

## Technical

- Depends on `account` only. Odoo 19 Community.
- Adds no new model. Four fields on `res.company`, one computed helper field
  on `account.move`, two QWeb inherits.
- If Odoo's Indian localisation (`l10n_in`) already has a UPI ID configured,
  this module stands aside rather than printing a second code.
- Install or upgrade with `-u drkds_in_upi_qr_invoice`; no service restart is
  needed beyond the usual upgrade.

The drkds GST suite adds GSTR-1 and GSTR-3B preparation, GSTR-2A
reconciliation and an e-invoice workflow.

Part of the drkds Indian SME suite for Odoo 19 Community.
