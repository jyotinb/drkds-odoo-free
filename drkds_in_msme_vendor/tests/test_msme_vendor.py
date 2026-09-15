from datetime import timedelta

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from ..models.res_partner import normalise_udyam


@tagged("post_install", "-at_install")
class TestMsmeVendor(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.env["account.move"])
        cls.company = cls.company_data["company"]
        cls.company.write({
            "drkds_msme_agreement_days": 45,
            "drkds_msme_no_agreement_days": 15,
            "drkds_msme_due_soon_days": 7,
        })
        Partner = cls.env["res.partner"]
        cls.micro = Partner.create({
            "name": "Micro Supplier",
            "drkds_msme_registered": True,
            "drkds_udyam_number": "UDYAM-DL-02-0012345",
            "drkds_msme_category": "micro",
            "drkds_msme_has_agreement": True,
        })
        cls.small_no_agreement = Partner.create({
            "name": "Small Supplier No Agreement",
            "drkds_msme_registered": True,
            "drkds_udyam_number": "UDYAM-MH-07-0009876",
            "drkds_msme_category": "small",
            "drkds_msme_has_agreement": False,
        })
        cls.medium = Partner.create({
            "name": "Medium Supplier",
            "drkds_msme_registered": True,
            "drkds_udyam_number": "UDYAM-KA-03-0004321",
            "drkds_msme_category": "medium",
        })
        cls.plain = Partner.create({"name": "Ordinary Supplier"})

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------
    @classmethod
    def _bill(cls, partner, days_ago=0, post=True, amount=1000.0):
        bill = cls.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": partner.id,
            "invoice_date": cls.today - timedelta(days=days_ago),
            "invoice_line_ids": [(0, 0, {
                "name": "Supply",
                "quantity": 1,
                "price_unit": amount,
                "tax_ids": [],
            })],
        })
        if post:
            bill.action_post()
        return bill

    # ------------------------------------------------------------------
    # The day clock
    # ------------------------------------------------------------------
    def test_clock_on_a_bill_dated_today(self):
        """A bill raised today sits 45 days away from its MSME due date."""
        bill = self._bill(self.micro)
        self.assertEqual(bill.drkds_msme_limit_days, 45)
        self.assertEqual(bill.drkds_msme_due_date, self.today + timedelta(days=45))
        self.assertEqual(bill.drkds_msme_days_outstanding, 0)
        self.assertEqual(bill.drkds_msme_days_overdue, 0)
        self.assertEqual(bill.drkds_msme_status, "within")

    def test_clock_on_a_bill_dated_fifty_days_ago(self):
        """Fifty days out on a 45 day limit is five days overdue."""
        bill = self._bill(self.micro, days_ago=50)
        self.assertEqual(bill.drkds_msme_due_date, self.today - timedelta(days=5))
        self.assertEqual(bill.drkds_msme_days_outstanding, 50)
        self.assertEqual(bill.drkds_msme_days_overdue, 5)
        self.assertEqual(bill.drkds_msme_status, "overdue")

    def test_due_soon_window(self):
        """Inside the due soon window the status warns before it breaches."""
        bill = self._bill(self.micro, days_ago=42)
        self.assertEqual(bill.drkds_msme_status, "due_soon")

    def test_acceptance_date_moves_the_clock(self):
        """Acceptance after the bill date pushes the due date out by the same days."""
        bill = self._bill(self.micro, days_ago=50, post=False)
        bill.drkds_msme_acceptance_date = self.today - timedelta(days=40)
        self.assertEqual(bill.drkds_msme_due_date, self.today + timedelta(days=5))
        self.assertEqual(bill.drkds_msme_status, "due_soon")

    # ------------------------------------------------------------------
    # Micro and small only
    # ------------------------------------------------------------------
    def test_medium_enterprise_is_out_of_scope(self):
        """Section 15 covers micro and small; a medium vendor has no clock."""
        self.assertFalse(self.medium.drkds_msme_covered)
        bill = self._bill(self.medium, days_ago=90)
        self.assertFalse(bill.drkds_msme_due_date)
        self.assertFalse(bill.drkds_msme_status)
        self.assertFalse(bill.drkds_msme_covered)

    def test_non_msme_vendor_gets_no_due_date(self):
        """A vendor that is not MSME registered is never tracked."""
        self.assertFalse(self.plain.drkds_msme_covered)
        bill = self._bill(self.plain, days_ago=120)
        self.assertFalse(bill.drkds_msme_due_date)
        self.assertEqual(bill.drkds_msme_days_outstanding, 0)
        self.assertFalse(bill.drkds_msme_status)

    def test_unticking_registration_clears_the_clock(self):
        bill = self._bill(self.micro, days_ago=10)
        self.assertTrue(bill.drkds_msme_due_date)
        self.micro.drkds_msme_registered = False
        self.assertFalse(bill.drkds_msme_due_date)

    # ------------------------------------------------------------------
    # The fifteen day variant
    # ------------------------------------------------------------------
    def test_no_written_agreement_is_fifteen_days(self):
        """With no agreement the buyer must pay before the appointed day."""
        self.assertEqual(
            self.small_no_agreement._drkds_msme_payment_days(self.company), 15
        )
        bill = self._bill(self.small_no_agreement, days_ago=20)
        self.assertEqual(bill.drkds_msme_limit_days, 15)
        self.assertEqual(bill.drkds_msme_due_date, self.today - timedelta(days=5))
        self.assertEqual(bill.drkds_msme_days_overdue, 5)
        self.assertEqual(bill.drkds_msme_status, "overdue")

    def test_same_bill_is_within_limit_with_an_agreement(self):
        """The only difference between the two vendors is the agreement flag."""
        self.small_no_agreement.drkds_msme_has_agreement = True
        bill = self._bill(self.small_no_agreement, days_ago=20)
        self.assertEqual(bill.drkds_msme_limit_days, 45)
        self.assertEqual(bill.drkds_msme_status, "within")

    def test_agreed_days_override_shortens_the_period(self):
        self.micro.drkds_msme_payment_days_override = 30
        bill = self._bill(self.micro, days_ago=35)
        self.assertEqual(bill.drkds_msme_limit_days, 30)
        self.assertEqual(bill.drkds_msme_status, "overdue")

    def test_agreed_days_cannot_exceed_the_statutory_cap(self):
        with self.assertRaises(ValidationError):
            self.micro.drkds_msme_payment_days_override = 60

    def test_company_days_are_settings_not_constants(self):
        """A stricter internal policy reprices existing bills."""
        bill = self._bill(self.micro, days_ago=35)
        self.assertEqual(bill.drkds_msme_status, "within")
        self.company.drkds_msme_agreement_days = 30
        self.assertEqual(bill.drkds_msme_limit_days, 30)
        self.assertEqual(bill.drkds_msme_status, "overdue")

    def test_company_days_cannot_exceed_the_statute(self):
        with self.assertRaises(ValidationError):
            self.company.drkds_msme_agreement_days = 60
        with self.assertRaises(ValidationError):
            self.company.drkds_msme_no_agreement_days = 20

    # ------------------------------------------------------------------
    # Udyam number
    # ------------------------------------------------------------------
    def test_valid_udyam_numbers_are_accepted(self):
        for number in ("UDYAM-DL-02-0012345", "UDYAM-MH-07-0009876",
                       "UDYAM-UP-11-1234567", "UDYAM-TN-00-0000001"):
            partner = self.env["res.partner"].create({
                "name": number,
                "drkds_msme_registered": True,
                "drkds_msme_category": "small",
                "drkds_udyam_number": number,
            })
            self.assertEqual(partner.drkds_udyam_number, number)

    def test_bad_udyam_numbers_are_refused(self):
        for number in (
            "UDYAM-DL-2-0012345",      # one digit district
            "UDYAM-DL-02-001234",      # six digit serial
            "UDYAM-D1-02-0012345",     # digit in the state code
            "UDYAM-ZZ-02-0012345",     # unknown state code
            "UDHYAM-DL-02-0012345",    # wrong prefix
            "DL-02-0012345",           # no prefix
            "0012345",                 # nonsense
        ):
            with self.assertRaises(ValidationError, msg=number):
                self.env["res.partner"].create({
                    "name": "Bad %s" % number,
                    "drkds_udyam_number": number,
                })

    def test_udyam_number_is_normalised(self):
        self.assertEqual(normalise_udyam(" udyam-dl-02-0012345 "),
                         "UDYAM-DL-02-0012345")
        self.assertEqual(normalise_udyam("udyamdl020012345"),
                         "UDYAM-DL-02-0012345")
        partner = self.env["res.partner"].create({
            "name": "Messy",
            "drkds_msme_registered": True,
            "drkds_msme_category": "micro",
            "drkds_udyam_number": " udyam dl 02 0012345 ",
        })
        self.assertEqual(partner.drkds_udyam_number, "UDYAM-DL-02-0012345")

    def test_blank_udyam_number_is_allowed(self):
        partner = self.env["res.partner"].create({"name": "No number"})
        self.assertFalse(partner.drkds_udyam_number)

    def test_registered_vendor_needs_a_category(self):
        with self.assertRaises(ValidationError):
            self.env["res.partner"].create({
                "name": "Registered but uncategorised",
                "drkds_msme_registered": True,
            })

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    def test_report_picks_up_exactly_the_breaching_bills(self):
        """Overdue micro and small bills only: not medium, not plain, not paid."""
        overdue_micro = self._bill(self.micro, days_ago=50)
        overdue_small = self._bill(self.small_no_agreement, days_ago=20)
        self._bill(self.micro, days_ago=10)            # within limit
        self._bill(self.medium, days_ago=200)          # out of scope
        self._bill(self.plain, days_ago=200)           # not MSME
        paid = self._bill(self.micro, days_ago=60)     # breached but settled

        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=paid.ids,
        ).create({"payment_date": self.today})._create_payments()
        self.assertEqual(paid.payment_state, "paid")
        self.assertEqual(paid.drkds_msme_status, "settled")

        Report = self.env["drkds.msme.outstanding.report"]
        breaching = Report.search([
            ("is_overdue", "=", True),
            ("company_id", "=", self.company.id),
        ])
        self.assertEqual(breaching.mapped("move_id"), overdue_micro | overdue_small)
        self.assertEqual(set(breaching.mapped("msme_category")), {"micro", "small"})
        self.assertTrue(all(r.days_overdue > 0 for r in breaching))

    def test_report_ageing_buckets(self):
        self._bill(self.micro, days_ago=5)
        self._bill(self.micro, days_ago=25)
        self._bill(self.micro, days_ago=100)
        Report = self.env["drkds.msme.outstanding.report"]
        records = Report.search([("company_id", "=", self.company.id)])
        buckets = set(records.mapped("ageing_bucket"))
        self.assertTrue({"0_15", "16_30", "90_plus"} <= buckets)

    def test_report_excludes_draft_bills(self):
        draft = self._bill(self.micro, days_ago=90, post=False)
        self.assertEqual(draft.state, "draft")
        Report = self.env["drkds.msme.outstanding.report"]
        self.assertFalse(Report.search([("move_id", "=", draft.id)]))

    def test_current_financial_year_flag(self):
        """The Indian financial year runs April to March."""
        Move = self.env["account.move"]
        start, end = Move._drkds_msme_fy_bounds(self.today)
        self.assertEqual((start.month, start.day), (4, 1))
        self.assertEqual((end.month, end.day), (3, 31))
        self.assertEqual(end.year, start.year + 1)
        bill = self._bill(self.micro, days_ago=0)
        self.assertEqual(bill.drkds_msme_fy, "%s-%s" % (start.year, str(end.year)[-2:]))
        record = self.env["drkds.msme.outstanding.report"].search([
            ("move_id", "=", bill.id),
        ])
        self.assertTrue(record.in_current_fy)

    def test_status_search_finds_overdue_bills(self):
        overdue = self._bill(self.micro, days_ago=50)
        self._bill(self.micro, days_ago=1)
        found = self.env["account.move"].search([
            ("drkds_msme_status", "=", "overdue"),
            ("company_id", "=", self.company.id),
        ])
        self.assertIn(overdue, found)
        self.assertTrue(all(m.drkds_msme_status == "overdue" for m in found))
