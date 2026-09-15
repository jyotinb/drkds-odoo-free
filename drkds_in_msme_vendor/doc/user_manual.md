# MSME Vendor Payment Tracking — user manual

## 1. What the module tracks, and what it does not

It tracks one thing well: how long a posted, unpaid vendor bill owed to a
registered **micro or small** enterprise has been outstanding, against the
limit in section 15 of the MSMED Act, 2006.

It does **not** compute the section 43B(h) disallowance, and it does not
compute section 16 interest. This module is a tool to assist with compliance
workflows. Responsibility for statutory compliance rests with the user and
their tax professional.

## 2. The rule, in one page

Section 15 of the MSMED Act, 2006: where a micro or small enterprise supplies
goods or renders services, the buyer must pay on or before the date agreed in
writing; and in no case may the agreed period exceed **45 days** from the day
of acceptance or the day of deemed acceptance. Where there is no agreement in
writing, the buyer must pay before the **appointed day**, which section 2(b)
defines as the day following immediately after the expiry of **15 days** from
the day of acceptance.

Section 43B(h) of the Income Tax Act, 1961 then disallows the deduction for
that expense until it is actually paid, if it was not paid inside that period.

Two things follow that people get wrong:

1. **Medium enterprises are excluded.** Section 15 names micro and small
   suppliers. A medium vendor with a Udyam number is not on this clock.
2. **The default is 15 days, not 45.** 45 days is the ceiling on what may be
   *agreed in writing*. With no written agreement the limit is 15.

## 3. Setting up a vendor

Contacts → open the vendor → **MSME** tab.

1. Tick **MSME Registered**.
2. Enter the **Udyam Number** in the format `UDYAM-XX-00-0000000`, for example
   `UDYAM-DL-02-0012345`. Spacing and case do not matter; the number is
   normalised on save. An invalid number is refused at save time, so a typo
   never reaches a bill.
3. Choose the **Enterprise Category** from the Udyam certificate. This decides
   everything: micro and small are tracked, medium is not. A blue note appears
   on a medium vendor to say so.
4. Enter the **MSME Registration Date** from the certificate.
5. Under **Payment Clock**, tick **Written Payment Agreement** if a written
   agreement fixes the credit period. Leave it unticked for the 15 day rule.
6. Optionally set **Agreed Days** if the written agreement specifies a period
   shorter than the company default. You cannot enter more than the company
   maximum; the statute does not allow contracting out of 45 days.

**MSME Payment Days** then shows the limit that will be applied to this
vendor's bills.

## 4. Company settings

Accounting → Configuration → Settings → **MSME Payment Clock (India)**.

| Setting | Default | Ceiling |
| --- | --- | --- |
| With a written agreement | 45 days | 45 |
| Without a written agreement | 15 days | 15 |
| Due soon window | 7 days | — |

They are per company, so a group with different internal policies is fine. You
may set a stricter period; you may not set a longer one. Saving a change
recomputes the MSME due date on existing vendor bills straight away.

## 5. On a vendor bill

For a registered micro or small vendor the bill shows:

- **Acceptance Date** — leave it empty and the bill date is used. Fill it only
  where acceptance genuinely happened later, for example after inspection. The
  clock runs from this date.
- **MSME Due Date** — acceptance date plus the limit.
- **MSME Limit (Days)** — the limit applied, so the figure is auditable.
- **Days Outstanding** — from acceptance to today, while unpaid.
- **MSME Status** — Within Limit, Due Soon, Overdue, or Settled once paid.

An **Overdue** bill carries a red banner at the top of the form naming the due
date and the days lost. A bill inside the due soon window carries an amber one.

Bills for a medium vendor, an unregistered vendor, or a customer invoice show
none of this.

## 6. The report

Accounting → Reporting → **MSME Outstanding Payments**.

It lists every posted, unpaid vendor bill owed to a registered micro or small
enterprise, grouped by vendor out of the box, with:

- **Ageing Bucket** — 0-15, 16-30, 31-45, 46-60, 61-90 and over 90 days
  outstanding.
- **Days Overdue** and a **Breaches Limit** flag.
- **Financial Year** on the Indian April-to-March year.
- Views: list, pivot (vendor by ageing bucket) and bar graph.

Filters:

- **Breaches the Limit** — everything past its MSME due date.
- **Current Financial Year** — bills dated in the running April-to-March year.
- **Breaching, Current Financial Year** — the two together. This is the list an
  auditor asks for at year end.

All ageing figures are computed live against today's date. There is no
scheduled job and nothing to refresh.

## 7. Finding overdue bills from the bills list

Accounting → Vendors → Bills, then the filters **MSME Vendor** and **MSME
Overdue**. Group by **Financial Year** to see the breach spread across years.

## 8. Frequently asked

**A vendor's category changed from small to medium. What happens?**
Change the category on the contact. The clock stops immediately and existing
bills lose their MSME due date, because they are no longer covered by section
15. Historical evidence for a closed year should be exported before changing.

**We paid the bill late. What is the disallowance?**
This module will not tell you, by design. Take the report to your tax
professional.

**Does anything contact the Udyam portal?**
No. Validation is offline and checks structure and the state code only.

---

This module is a tool to assist with compliance workflows. Responsibility for
statutory compliance rests with the user and their tax professional.

Part of the drkds Indian SME suite for Odoo 19 Community.
