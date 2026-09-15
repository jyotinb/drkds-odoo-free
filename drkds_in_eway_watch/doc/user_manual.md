# E-Way Bill Expiry Watch — user manual

## 1. What this module is

An add-on to Odoo Community's **Indian E-waybill** module
(`l10n_in_ewaybill`). That module generates the e-way bill through the
government channel and stores the number, date and validity date it gets back.
**This module generates nothing.** It watches what core already stored and
tells you when a bill is about to lapse, or has.

If `l10n_in_ewaybill` is not installed and configured with your GSP
credentials, install that first. Nothing here works without it.

## 2. Configure once

Accounting → Configuration → Settings → **E-Way Bill Watch (India)**.

| Setting | Default | Why it is a setting |
|---|---|---|
| E-Way Bill Threshold | 50,000 | Fifty thousand rupees is the usual inter-state figure; several states set a different limit for movement inside the state |
| Kilometres per Day of Validity | 200 | Rule 138(10) moved from 100 to 200 km with effect from 1 January 2021; over dimensional cargo is 20 km |

Neither setting changes anything Odoo sends to the government. The kilometres
figure only drives a suggestion shown for comparison.

## 3. The watch list

Accounting → Accounting → **E-Way Bill Watch**.

The list opens grouped by expiry status:

- **Active** — more than a day of validity left.
- **Expiring Soon** — one day or less left. Amber row.
- **Expired** — the validity date has passed. Red row.
- **Cancelled** — cancelled through core's own cancel wizard.
- **Not Generated** — the e-way bill record exists but has not been sent yet.

Filters: **Expiring within 24 hours**, **Expiring within 3 days**, **Expired**,
**Validity Differs from Rule**, **Cancelled**. Group by **Expiry Status**,
**Transporter**, **Transport Mode** or **E-Way Bill Date**.

Core ships no list view and no filters for e-way bills at all, so all of this
is added rather than modified.

### Why the status on the form still says "Generated"

Look at an expired bill and you will see two statuses: Odoo's **Status** still
says Generated, and **Expiry Status** says Expired. That is deliberate.

Odoo's `state` field records what the government portal said when the bill was
created, and its values come from API responses. Adding an "expired" value to
that selection would mean writing our own value into a field another module
drives from a government reply — fragile, and wrong in principle, because the
portal never told Odoo the bill expired. The expiry status is therefore our own
field, derived from the validity date, and core's is left untouched.

## 4. The daily job

Settings → Technical → Scheduled Actions → **E-Way Bill: refresh expiry
status**, daily.

Expiry depends on today's date, which no database dependency can trigger: left
alone, a bill would only turn red when somebody happened to save it. The job
recomputes the status for every generated bill and posts one message in the
chatter of each bill that has lapsed since it last ran, so a stale e-way bill
reaches a follower's inbox instead of waiting to be noticed. The message is
posted once per bill, never repeatedly.

## 5. Validity, and the suggestion

Rule 138(10) of the CGST Rules: one day for every 200 km **or part thereof**,
counted from generation.

| Distance | Days |
|---|---|
| 150 km | 1 |
| 200 km | 1 |
| 201 km | 2 |
| 450 km | 3 |

Source: rule 138(10), as amended by Notification 94/2020-Central Tax with
effect from 1 January 2021, which replaced the earlier 100 km figure. For over
dimensional cargo set kilometres per day to 20.

On the e-way bill form, **Suggested Valid Upto** shows what that rule would
give for the declared distance. It is a sanity check, not an authority: the
date that counts is **e-Waybill Valid Upto**, which came from the portal. When
the portal's date is earlier than the rule would allow, **Validity Differs from
Rule** is ticked and the **Validity Differs from Rule** filter finds it. That
is usually harmless — a short-haul bill, or a distance entered differently from
what the portal computed pin-to-pin — but it is worth a look.

## 6. Invoices with no e-way bill

Accounting → Accounting → **Invoices Without an E-Way Bill**, or the **E-Way
Bill Missing** filter on the invoice list.

It lists posted customer invoices and credit notes at or above the threshold
with no *generated* e-way bill. A bill created but never sent does not count,
because it is not an e-way bill yet.

This is a reminder, not a rule. Nothing blocks posting, and nothing is raised:
exempt goods, short local movements and service invoices legitimately carry no
e-way bill. The threshold is not stored on the invoice, so raising or lowering
it takes effect on the list immediately.

## 7. Manual entry is not supported, on purpose

If you generate e-way bills on the NIC portal by hand rather than through
Odoo, this module cannot help you. Core owns the number, the date and the
validity date as API results and marks them readonly; making them writable so
a hand-typed number could be recorded would let a record claim a bill the
portal never issued, and would break the next time core changes. We chose not
to fight core over it.

---

This module is a tool to assist with compliance workflows. Responsibility for
statutory compliance rests with the user and their tax professional.

Part of the drkds Indian SME suite for Odoo 19 Community.
