# User manual — Rupee Amounts in Words (Lakh and Crore)

## 1. What this changes, and what it does not

Odoo already spells amounts out in words. You will have seen it as the
paragraph "Total amount in words" at the foot of an invoice, and as the words
line on a printed cheque. This module does **not** add that feature.

What it changes is the **scale** a rupee amount is read on.

Odoo builds the words with the `num2words` library, asking it for the wording
in the interface language of the user who is printing. `num2words` genuinely
knows the Indian numbering system — it has an `en_IN` locale that returns lakh
and crore. So a user running the **English (IN)** language already gets the
right words, with no module at all.

The trouble is that almost every Indian business runs Odoo in **English (US)**.
For them the very same rupee invoice prints:

| Figure | What Odoo prints in English (US) | What it should say |
| --- | --- | --- |
| 1,00,000 | One Hundred Thousand | One Lakh |
| 1,00,00,000 | Ten Million | One Crore |
| 1,00,00,00,000 | One Billion | One Hundred Crore |

The language somebody chose for their menus has nothing to do with the currency
being printed on the document. This module moves that decision onto the
currency: **if the amount is in rupees, it is read the Indian way.**

The invoice layout is untouched. Odoo's own switch still decides whether the
sentence is printed and where it sits on the page. Only the wording changes.

## 2. Turning it on

The feature is **on by default** once the module is installed. To see or change
it:

1. Go to **Accounting → Configuration → Settings**.
2. In the *Customer Invoices* block, find Odoo's switch **Total amount of
   invoice in letters**. This is Odoo's own, and it decides whether the
   sentence appears on the invoice PDF at all. Tick it if you want the
   paragraph printed.
3. Directly below it is **Indian Scale for Rupee Amounts**, added by this
   module, with its three wording options beneath.

Everything here is per company. A multi-company database can leave the Indian
entity on and an overseas entity off.

Switching **Indian Scale for Rupee Amounts** off restores Odoo's stock
behaviour exactly — language-driven wording, no suffix, no paise clause.

## 3. The wording options

| Setting | Default | What it does |
| --- | --- | --- |
| Indian Scale for Rupee Amounts | on | Read INR in lakh and crore regardless of language. |
| Words Connector | `and` | The word between the rupees and the paise. |
| Words Suffix | `Only` | The word that closes the sentence. |
| Spell Zero Paise | off | Whether a round figure still says "and Zero Paise". |

### Connector

- `and` → Rupees Five Hundred **and** Fifty Paise Only
- `Point` → Rupees Five Hundred **Point** Fifty Paise Only
- empty → Rupees Five Hundred Fifty Paise Only

### Suffix

The suffix is what stops a printed figure being extended by hand. `Only` is
the usual Indian choice; `Only (E. & O.E.)` is common on proforma documents.
Leaving it empty prints no suffix, which is what Odoo does on its own.

### Spell Zero Paise

Off: `Rupees Five Hundred Only`.
On: `Rupees Five Hundred and Zero Paise Only`.

Some banks and government departments reject the short form. Turn it on if
yours does.

## 4. What the words look like

| Figure | Words |
| --- | --- |
| 0 | Rupees Zero Only |
| 1 | Rupees One Only |
| 99 | Rupees Ninety-Nine Only |
| 1,000 | Rupees One Thousand Only |
| 1,00,000 | Rupees One Lakh Only |
| 1,00,00,000 | Rupees One Crore Only |
| 1,00,00,00,000 | Rupees One Hundred Crore Only |
| 500.50 | Rupees Five Hundred and Fifty Paise Only |
| -1,500.25 | Minus Rupees One Thousand Five Hundred and Twenty-Five Paise Only |

Above a crore the count keeps running in crore — 10⁹ is "One Hundred Crore",
not "One Arab". That is the `en_IN` locale's convention and it is the one
Indian banks, auditors and company accounts use.

Paise come from the currency's own decimal places, so 0.999 rounds up to
"Rupees One Only" rather than losing the rounding.

## 5. Currency names

"Rupees" and "Paise" come from the currency record, fields **Currency Unit**
and **Currency Subunit** on *Accounting → Configuration → Currencies*. Odoo
ships them empty; when they are blank this module uses "Rupees" and "Paise".
Fill them in and they are used verbatim — "Rupee" and "Paisa", for instance.

## 6. Where the corrected wording shows up

Because the fix is applied at the source — `res.currency.amount_to_text` —
every part of Odoo that spells an amount out is corrected at once:

- **Invoices, credit notes and vendor bills.** Odoo's `amount_total_words`
  field, printed by the standard switch.
- **Printed cheques.** The words line produced by *Check Printing*
  (`account_check_printing`), if you use it.

Those are the only two places in Odoo 19 Community that convert an amount to
text for a general currency. Payment receipts do not print an amount in words
at all. The Argentinian and Gulf localisations have their own wording on their
own report templates; they are not affected, because they are not used with
rupee amounts.

## 7. Tax amount in words

Indian invoices customarily show the tax figure in words as well as digits: it
is the figure a GST officer and a customer's accounts department both check by
hand, and a number written twice cannot be altered afterwards. Odoo has no
field for it, so this module adds one: **Tax Amount in Words**
(`drkds_tax_amount_in_words`) on the invoice.

It is computed and never stored, and it follows the same settings as the
total. To print it, add one line to your own report inherit:

```xml
<span t-field="o.drkds_tax_amount_in_words"/>
```

The same helper is available for any other amount — a round-off, an advance, a
TDS deduction:

```xml
<span t-out="o.currency_id.drkds_amount_in_words(some_amount, o.company_id)"/>
```

The module ships no report template of its own, so it will not collide with
whatever else you have inherited on the invoice.

## 8. Troubleshooting

**No words are printed on the invoice.** Odoo's switch *Total amount of
invoice in letters* is off. Turn it on in Accounting settings.

**It still reads in millions.** Either *Indian Scale for Rupee Amounts* is
off, or the invoice is not in INR. The scale follows the currency on the
document, not the company.

**The words say "Indian Rupee" instead of "Rupees".** Something has filled the
**Currency Unit** field on the INR currency. Clear it, or set it to the
wording you want.

**Nothing at all is spelled out, in any currency.** The `num2words` library is
missing from the Python environment. Odoo needs it too; install it.

Part of the drkds Indian SME suite for Odoo 19 Community.
