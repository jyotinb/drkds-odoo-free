from datetime import date, timedelta

from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon
from odoo.tests import tagged

from ..models.l10n_in_ewaybill import validity_days


@tagged("post_install_l10n", "post_install", "-at_install")
class TestEwayWatch(L10nInTestInvoicingCommon):
    """The watch layer: expiry status, the daily job, and the threshold list."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Ewaybill = cls.env["l10n.in.ewaybill"]
        cls.today = date.today()
        cls.company = cls.env.company
        cls.company.write({
            "drkds_eway_km_per_day": 200,
            "drkds_eway_threshold": 50000.0,
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _invoice(self, price=60000.0, post=True):
        invoice = self.init_invoice("out_invoice", post=False, products=self.product_a)
        invoice.invoice_line_ids.write({"price_unit": price, "quantity": 1, "discount": 0})
        if post:
            invoice.action_post()
        return invoice

    def _ewaybill(self, invoice, distance=20, **values):
        return self.Ewaybill.create({
            "account_move_id": invoice.id,
            "distance": distance,
            "type_id": self.env.ref("l10n_in_ewaybill.type_tax_invoice_sub_type_supply").id,
            "mode": "1",
            "vehicle_no": "GJ11AA1234",
            "vehicle_type": "R",
            **values,
        })

    def _generated(self, invoice, expiry, distance=20, generated_on=None):
        """A bill in the state the API would have left it in."""
        bill = self._ewaybill(invoice, distance=distance)
        bill.write({
            "state": "generated",
            "name": "123456789012",
            "ewaybill_date": generated_on or self.today,
            "ewaybill_expiry_date": expiry,
        })
        return bill

    # ------------------------------------------------------------------
    # Validity rule 138(10)
    # ------------------------------------------------------------------
    def test_validity_days_rule_138(self):
        """One day per 200 km or part thereof, at the default setting."""
        self.assertEqual(validity_days(150), 1)
        self.assertEqual(validity_days(200), 1)
        self.assertEqual(validity_days(201), 2)
        self.assertEqual(validity_days(450), 3)
        self.assertEqual(validity_days(0), 1)

    def test_validity_days_follows_company_setting(self):
        """Over dimensional cargo at 20 km per day gives a much shorter bill."""
        self.assertEqual(validity_days(150, km_per_day=20), 8)
        self.assertEqual(validity_days(150, km_per_day=100), 2)

    def test_suggested_expiry_from_distance(self):
        bill = self._generated(self._invoice(), self.today + timedelta(days=3), distance=450)
        self.assertEqual(bill.drkds_suggested_expiry, self.today + timedelta(days=3))
        self.assertFalse(bill.drkds_validity_mismatch)

    def test_suggested_expiry_follows_company_setting(self):
        """Switching the company to over dimensional cargo lengthens the estimate."""
        bill = self._generated(self._invoice(), self.today + timedelta(days=1), distance=150)
        self.assertEqual(bill.drkds_suggested_expiry, self.today + timedelta(days=1))
        self.company.drkds_eway_km_per_day = 20
        bill.invalidate_recordset(["drkds_suggested_expiry", "drkds_validity_mismatch"])
        self.assertEqual(bill.drkds_suggested_expiry, self.today + timedelta(days=8))

    def test_validity_mismatch_flag(self):
        """A portal validity shorter than the rule allows is flagged."""
        bill = self._generated(self._invoice(), self.today + timedelta(days=1), distance=450)
        self.assertTrue(bill.drkds_validity_mismatch)

    def test_mismatch_filter_is_searchable(self):
        """The filter's domain has to resolve, computed field or not."""
        Ewaybill = self.env["l10n.in.ewaybill"]
        short = self._generated(self._invoice(), self.today + timedelta(days=1), distance=450)
        fine = self._generated(self._invoice(), self.today + timedelta(days=3), distance=450)
        found = Ewaybill.search([("drkds_validity_mismatch", "=", True)])
        self.assertIn(short, found)
        self.assertNotIn(fine, found)
        self.assertIn(fine, Ewaybill.search([("drkds_validity_mismatch", "=", False)]))
        self.assertIn(short, Ewaybill.search([("drkds_validity_mismatch", "in", [True])]))
        self.assertNotIn(short, Ewaybill.search([("drkds_validity_mismatch", "not in", [True])]))

    def test_no_estimate_without_a_generation_date(self):
        bill = self._ewaybill(self._invoice())
        self.assertFalse(bill.drkds_suggested_expiry)
        self.assertFalse(bill.drkds_validity_mismatch)

    # ------------------------------------------------------------------
    # Expiry status
    # ------------------------------------------------------------------
    def test_status_pending_before_generation(self):
        bill = self._ewaybill(self._invoice())
        self.assertEqual(bill.state, "pending")
        self.assertEqual(bill.drkds_watch_status, "pending")

    def test_status_active(self):
        bill = self._generated(self._invoice(), self.today + timedelta(days=5))
        self.assertEqual(bill.drkds_watch_status, "active")
        self.assertEqual(bill.drkds_days_to_expiry, 5)

    def test_status_expiring_soon_within_24_hours(self):
        bill = self._generated(self._invoice(), self.today + timedelta(days=1))
        self.assertEqual(bill.drkds_watch_status, "expiring")
        self.assertEqual(bill.drkds_days_to_expiry, 1)

    def test_status_expired_with_a_past_date(self):
        bill = self._generated(self._invoice(), self.today - timedelta(days=2))
        self.assertEqual(bill.drkds_watch_status, "expired")
        self.assertEqual(bill.drkds_days_to_expiry, -2)

    def test_boundary_expiring_today_is_not_expired(self):
        """A bill valid until today is still valid today.

        Off by one here would tell a driver holding a live e-way bill that it
        has lapsed, so both sides of the boundary are pinned down.
        """
        bill = self._generated(self._invoice(), self.today)
        self.assertEqual(bill.drkds_days_to_expiry, 0)
        self.assertEqual(bill.drkds_watch_status, "expiring")
        self.Ewaybill._cron_drkds_refresh_watch_status()
        self.assertEqual(bill.drkds_watch_status, "expiring", "the cron must not expire it early")
        self.assertFalse(bill.drkds_expiry_logged)

    def test_boundary_expiring_yesterday_is_expired(self):
        bill = self._generated(self._invoice(), self.today - timedelta(days=1))
        self.assertEqual(bill.drkds_days_to_expiry, -1)
        self.assertEqual(bill.drkds_watch_status, "expired")

    def test_core_state_is_left_alone(self):
        """The watch never touches core's own status selection."""
        bill = self._generated(self._invoice(), self.today - timedelta(days=2))
        self.assertEqual(bill.state, "generated")
        self.assertNotIn("expired", dict(bill._fields["state"].selection))

    def test_status_cancelled(self):
        bill = self._generated(self._invoice(), self.today + timedelta(days=5))
        bill.state = "cancel"
        self.assertEqual(bill.drkds_watch_status, "cancelled")

    # ------------------------------------------------------------------
    # The daily job
    # ------------------------------------------------------------------
    def test_cron_moves_a_lapsed_bill_to_expired_and_logs_once(self):
        """Time passing, not a write, is what expires a bill."""
        bill = self._generated(self._invoice(), self.today + timedelta(days=1))
        self.assertEqual(bill.drkds_watch_status, "expiring")

        # The clock moves past the validity date with nothing writing to the
        # record. Flush first: the ORM still holds the written expiry date as a
        # pending update, and the next flush would write it straight back over
        # the raw SQL below, which is what this test is trying to simulate
        # around -- in production the cron simply opens a new transaction on a
        # later day.
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE l10n_in_ewaybill SET ewaybill_expiry_date = %s WHERE id = %s",
            (self.today - timedelta(days=1), bill.id),
        )
        bill.invalidate_recordset(["ewaybill_expiry_date"])
        self.assertEqual(
            bill.ewaybill_expiry_date, self.today - timedelta(days=1),
            "the premise of this test: the stored validity date really is in the past",
        )
        self.assertEqual(bill.drkds_watch_status, "expiring", "stale until the job runs")

        before = len(bill.message_ids)
        self.Ewaybill._cron_drkds_refresh_watch_status()
        self.assertEqual(bill.drkds_watch_status, "expired")
        self.assertTrue(bill.drkds_expiry_logged)
        self.assertEqual(len(bill.message_ids), before + 1)

        # A second run must not post the same message again.
        self.Ewaybill._cron_drkds_refresh_watch_status()
        self.assertEqual(len(bill.message_ids), before + 1)

    def test_cron_leaves_a_live_bill_alone(self):
        bill = self._generated(self._invoice(), self.today + timedelta(days=5))
        before = len(bill.message_ids)
        self.Ewaybill._cron_drkds_refresh_watch_status()
        self.assertEqual(bill.drkds_watch_status, "active")
        self.assertFalse(bill.drkds_expiry_logged)
        self.assertEqual(len(bill.message_ids), before)

    # ------------------------------------------------------------------
    # Threshold reminder
    # ------------------------------------------------------------------
    def _missing(self):
        return self.env["account.move"].search([("drkds_eway_missing", "=", True)])

    def test_above_threshold_without_eway_is_flagged(self):
        invoice = self._invoice(price=60000.0, post=False)
        self.assertFalse(invoice.drkds_eway_missing, "a draft invoice is not flagged")
        invoice.action_post()
        self.assertTrue(invoice.drkds_eway_missing)
        self.assertIn(invoice, self._missing())

    def test_below_threshold_is_not_flagged(self):
        invoice = self._invoice(price=40000.0)
        self.assertFalse(invoice.drkds_eway_missing)
        self.assertNotIn(invoice, self._missing())

    def test_generated_eway_clears_the_flag(self):
        invoice = self._invoice(price=60000.0)
        self.assertTrue(invoice.drkds_eway_missing)
        self._generated(invoice, self.today + timedelta(days=2))
        invoice.invalidate_recordset(["drkds_eway_missing"])
        self.assertFalse(invoice.drkds_eway_missing)
        self.assertNotIn(invoice, self._missing())

    def test_pending_eway_does_not_clear_the_flag(self):
        """A bill created but never generated is not an e-way bill yet."""
        invoice = self._invoice(price=60000.0)
        self._ewaybill(invoice)
        invoice.invalidate_recordset(["drkds_eway_missing"])
        self.assertTrue(invoice.drkds_eway_missing)
        self.assertIn(invoice, self._missing())

    def test_threshold_change_is_live(self):
        """The flag is not stored, so raising the threshold takes effect at once."""
        invoice = self._invoice(price=60000.0)
        self.assertIn(invoice, self._missing())
        self.company.drkds_eway_threshold = 100000.0
        invoice.invalidate_recordset(["drkds_eway_missing"])
        self.assertFalse(invoice.drkds_eway_missing)
        self.assertNotIn(invoice, self._missing())

    def test_search_handles_in_and_not_in(self):
        """The ORM passes in / not in for boolean domains, not only = and !=."""
        Move = self.env["account.move"]
        invoice = self._invoice(price=60000.0)
        self.assertIn(invoice, Move.search([("drkds_eway_missing", "in", [True])]))
        self.assertNotIn(invoice, Move.search([("drkds_eway_missing", "in", [False])]))
        self.assertNotIn(invoice, Move.search([("drkds_eway_missing", "not in", [True])]))
        self.assertIn(invoice, Move.search([("drkds_eway_missing", "not in", [False])]))

    def test_negative_search_is_the_complement(self):
        invoice = self._invoice(price=60000.0)
        not_missing = self.env["account.move"].search([("drkds_eway_missing", "=", False)])
        self.assertNotIn(invoice, not_missing)
