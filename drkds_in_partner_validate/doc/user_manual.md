# User manual

## What this module adds, and what Odoo already did

Odoo itself already refuses a GSTIN of the wrong shape: the check lives in the
standard `base_vat` module and runs on the **Tax ID** field of any contact in
India. It is a pattern test only, and it stops there.

This module adds the three checks that pattern test cannot make:

- the **check digit**, the fifteenth character,
- the **state** inside the GSTIN against the state on the address,
- the **PAN** inside the GSTIN against the PAN field.

## Where the fields are

The GSTIN is the standard **Tax ID** field. This module does not add a second
GSTIN field, because Odoo's Indian localisation also reads the GSTIN from Tax
ID and two competing fields would split your data.

Under Tax ID you will find **PAN**, **IFSC**, and, once a GSTIN is recognised,
the **GST State** it resolves to. All are optional; a contact with none of them
saves normally.

## Entering a GSTIN

Type or paste the fifteen character number into Tax ID. Spacing, dashes and
lower case are cleaned up for you, so `27 aapfu0939f1zv` is stored as
`27AAPFU0939F1ZV`. A tax id that does not look like a GSTIN is left untouched,
so foreign contacts are unaffected.

The number is refused if:

- it is not one of the GSTIN patterns Odoo recognises (Odoo's own check),
- the last character does not match the check digit computed from the other
  fourteen, which catches a mistyped or transposed digit,
- its first two digits name a different state from the one on the address,
- the PAN inside it disagrees with the PAN field.

A check digit failure names the character that was expected, so the number can
be corrected rather than merely rejected.

## Which GSTINs get the check digit test

Only the **ordinary form**: a two digit state code, a PAN, an entity digit, the
letter Z and the check character. That is the form almost every business
carries.

The other four forms Odoo accepts — UN and ON body, NRI, TDS and TCS — are
passed through on Odoo's pattern check alone, with **no** checksum test. This
is deliberate. The published check-digit convention is not confirmed for those
series, and wrongly refusing a real registration would be far worse than
letting a mistyped one through. If you hold such a number, it will save.

The EDI test GSTIN used by Odoo's Indian localisation is likewise never
check-digit tested, so installing this module alongside `l10n_in` changes
nothing about it.

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
to three of them. This never blocks the save, because a GSTIN is sometimes
re-keyed onto a second record on purpose.

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
