# User manual

## Where the fields are

Open any contact. Under the tax identification field on the form you will find
four new fields: **GSTIN**, **PAN**, **IFSC** and, once a GSTIN is filled, the
**GST State** it resolves to.

All four are optional. A contact with none of them saves normally.

## Entering a GSTIN

Type or paste the fifteen character number. Spacing, dashes and lower case are
cleaned up for you, so `27 aapfu0939f1zv` is stored as `27AAPFU0939F1ZV`.

The number is refused if:

- it is not fifteen characters in the GSTIN pattern,
- the last character does not match the check digit computed from the other
  fourteen, which catches a mistyped or transposed digit,
- its first two digits name a different state from the one on the address,
- the PAN inside it disagrees with the PAN field.

Each refusal names the problem and, for a check digit failure, tells you which
character was expected.

## Entering a PAN

Five letters, four digits, one letter. The fourth character is the holder type
and is checked against the letters the income tax department issues, so a typo
there is caught rather than stored.

## Entering an IFSC

Eleven characters: four letters, a zero, then six more characters.

## PIN codes

On a contact whose country is India, the postal code must be six digits and may
not begin with zero. Contacts in other countries keep their own postal format
untouched.

## The duplicate notice

If another contact already carries the same GSTIN, a notice appears naming up
to three of them. This never blocks the save. Branches and divisions of one
business legitimately share a PAN, and sometimes a GSTIN is re-keyed onto a
second record on purpose.

## Maintaining the state code table

Go to **Settings > Technical > GST State Codes**. Each row is a two digit code,
a name and an optional link to an Odoo state. Only rows with a link take part in
the GSTIN versus address cross-check.

Ladakh and Other Territory ship without a link because Odoo does not carry a
matching state record for them, so a GSTIN in those states is checked for
structure and check digit but not against the address.

## Disclaimer

This module is a tool to assist with compliance workflows. Responsibility for
statutory compliance rests with the user and their tax professional.
