{
    "name": "Rupee Amounts in Words (Lakh and Crore)",
    "summary": "Make Odoo's amount in words read rupees in lakh and crore, whatever language the user runs",
    "description": """
Rupee Amounts in Words (Lakh and Crore)
=======================================

Odoo already prints an amount in words. This module does not add that feature;
it corrects the scale it is read on for rupee amounts.

The problem
-----------
Odoo spells amounts out through ``res.currency.amount_to_text``, which asks
``num2words`` for the wording using the **interface language of the user**.
``num2words`` does know the Indian scale, under the ``en_IN`` locale, so a user
running the English (IN) language already gets "One Lakh" without this module.

Almost no Indian business runs Odoo in English (IN). They run English (US),
and their rupee invoices therefore print:

    One Hundred Thousand ... Ten Million ... One Billion

on a document that goes to a customer, and sometimes to a bank. The language a
user picked for their menus has nothing to do with the currency being printed.

What this module does
---------------------
* **Keys the scale off the currency.** When the amount is in INR it is read
  with the ``en_IN`` locale - thousand, lakh, crore - whatever language the
  user is running and whatever country the company is in.
* **Leaves every other currency alone.** A dollar or euro amount is handed
  straight back to Odoo's own converter, unchanged.
* **Fixes every place at once.** The override sits on ``amount_to_text``
  itself, so the invoice total in letters and the amount in words on a printed
  cheque are both corrected, along with anything else that calls it.
* **Adds paise and a suffix.** Core's sentence is bare. Here the fractional
  part is read as paise and the sentence closes with "Only", the word that
  stops a printed figure being extended by hand.
* **Configurable wording.** The connector word, the suffix, and whether a
  round figure still says "and Zero Paise" are company settings, because banks
  and government departments each insist on their own phrasing.
* **Tax amount in words.** Indian invoices customarily carry the tax figure in
  words as well as digits. Core has no field for it; this module adds one.

What it does not do
-------------------
* It does not change the invoice PDF layout. Odoo's existing switch
  *Total amount of invoice in letters* still decides whether the sentence is
  printed, and where. Only the wording changes.
* It does not add a second "amount in words" field for the total. Core's
  ``amount_total_words`` is the field, and it now reads correctly.
* It writes no number-to-words code of its own. ``num2words`` is already a
  hard dependency of Odoo and its Indian locale is correct; this module points
  Odoo at it.

Settings live in Accounting > Configuration > Settings, directly under Odoo's
own total-in-letters switch, and are per company.

The drkds Accounting India app adds GSTR-1 and GSTR-3B preparation, GSTR-2A reconciliation, TDS and TCS with Form 26Q and an E-Way Bill register.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Accounting/Localizations",
    "author": "drkds",
    "website": "https://github.com/drkds/drkds-odoo-free",
    "license": "LGPL-3",
    "depends": ["account"],
    "external_dependencies": {"python": ["num2words"]},
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "images": ["static/description/cover.png"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
