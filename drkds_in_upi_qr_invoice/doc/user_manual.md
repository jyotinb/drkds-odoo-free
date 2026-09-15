# User manual — UPI Payment QR on Invoices (India)

## 1. What this module does

It prints a UPI QR code on customer invoices. The customer scans it with any
UPI application — GPay, PhonePe, Paytm, a bank app — and pays. The payee, the
amount still due and the invoice reference are already in the code.

## 2. Setting it up

1. Go to **Settings > Accounting**, section **Customer Payments**.
2. Find **UPI Payment QR (India)**.
3. Fill in **UPI ID (VPA)** — the address your money should arrive at, for
   example `acme@okhdfcbank`. This is the only required setting.
4. Optionally set **Payee Name**. If you leave it empty the company name is
   used. This is what the customer sees in their UPI app before they enter
   their PIN, so use the name they will recognise.
5. Decide the two switches:
   - **Pre-fill the amount due** — on by default. Off prints an open code and
     the customer types their own amount, which suits deposits and part
     payments.
   - **Include the invoice reference** — on by default. It is what lets you
     match an incoming credit back to an invoice.
6. Save.

The UPI ID is checked as you save. If it is not of the form `name@handle`
Odoo refuses the save and tells you what is wrong. Clearing the field is
always allowed: it just means no QR code is printed anywhere.

## 3. Where the code appears

- **The invoice PDF**, beside the payment information block, with the UPI ID
  printed underneath for customers who prefer to type it.
- **The customer portal invoice page**, as a card above the invoice preview.

## 4. When the code is not printed

By design, and this is deliberate rather than a limitation:

| Situation | Why |
| --- | --- |
| Vendor bill | The money moves the other way. |
| Credit note | You owe the customer, not the reverse. |
| Draft invoice | It is not a demand for payment yet. |
| Fully paid invoice | Nothing is due. |
| No UPI ID configured | Nothing to pay into. |
| Non-INR invoice with the amount switch on | UPI settles in INR only. |

If a customer pays part of an invoice, the next PDF you send carries a code
for the remaining balance, not the original total.

## 5. Matching payments

With **Include the invoice reference** on, the payment carries the invoice's
payment reference (or its number) as the UPI transaction reference and as the
note. Your bank statement line then shows that reference, which makes the
reconciliation obvious.

This module does not fetch or reconcile payments by itself. It writes the
reference into the code; recording the receipt stays a normal Odoo payment.

## 6. Troubleshooting

**No code on the PDF.** Check, in order: the invoice is posted, it is a
customer invoice, something is still due, the company on the invoice has a
UPI ID, and the currency is INR when the amount switch is on.

**Two codes on the PDF.** Odoo's Indian localisation has its own UPI QR
feature. When a UPI ID is set there, this module stands aside. Clear the
localisation's field if you prefer this module's code.

**The app shows the wrong name.** Payment apps often display the name
registered with the bank for that VPA rather than the `pn` value. That is the
UPI network's behaviour, not something a QR code can override.

Part of the drkds Indian SME suite for Odoo 19 Community.
