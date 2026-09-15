# Rupee Amounts in Words (Lakh and Crore)

Odoo **already** prints an amount in words. This module does not add that
feature. It fixes the scale that rupee amounts are read on.

## The problem

Odoo spells amounts out through `res.currency.amount_to_text`, which asks
`num2words` for the wording using the **interface language of the user**.
`num2words` does know the Indian scale, under its `en_IN` locale, so a user
running the English (IN) language already gets "One Lakh" without this module.

Almost no Indian business runs Odoo in English (IN). They run English (US),
and their rupee invoices therefore print:

> One Hundred Thousand … Ten Million … One Billion

on a document that goes to a customer, and sometimes to a bank. The language a
user picked for their menus has nothing to do with the currency being printed.

## What this module does

- **Keys the scale off the currency.** An INR amount is read with the `en_IN`
  locale whatever language the user runs and whatever country the company is
  in. Not the user language, not the company country — the currency.
- **Leaves every other currency alone.** USD, EUR and the rest are handed
  straight back to Odoo's own converter, unchanged.
- **Fixes every place at once.** The override sits on `amount_to_text` itself,
  so both core callers are corrected: the invoice total in letters
  (`account.move.amount_total_words`) and the amount in words on a printed
  cheque (`account_check_printing`).
- **Adds paise and a suffix.** Core's sentence is bare. Here the fractional
  part is read as paise and the sentence closes with "Only".
- **Configurable wording**, per company: connector word, closing suffix, and
  whether a round figure still says "and Zero Paise".
- **Tax amount in words** — `drkds_tax_amount_in_words` on `account.move`.
  Indian invoices customarily carry it and Odoo has no equivalent field.

## What it does not do

- It does not change the invoice PDF layout. Odoo's `Total amount of invoice
  in letters` switch still decides whether the sentence prints, and where.
- It does not add a second total-in-words field. `amount_total_words` is the
  field, and it now reads correctly.
- It writes no number-to-words code of its own.

## Settings

**Accounting → Configuration → Settings**, directly under Odoo's own
*Total amount of invoice in letters* switch. Per company. Turning
*Indian Scale for Rupee Amounts* off restores Odoo's stock behaviour exactly.

## Install

Copy into the addons path and install `drkds_in_inr_words`. `num2words` is
already a hard dependency of Odoo, so nothing extra is required. No upgrade of
other modules is needed; the module only inherits.

Licence LGPL-3. Odoo 19 Community.

The drkds Accounting India app adds GSTR-1 and GSTR-3B preparation, GSTR-2A reconciliation, TDS and TCS with Form 26Q and an E-Way Bill register.

Part of the drkds Indian SME suite for Odoo 19 Community.
