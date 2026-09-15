from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

from ..models.res_partner import gstin_check_digit


@tagged("post_install", "-at_install")
class TestPartnerIdentifiers(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.india = cls.env.ref("base.in")
        cls.maharashtra = cls.env.ref("base.state_in_mh")
        cls.gujarat = cls.env.ref("base.state_in_gj")

    # -- check digit ---------------------------------------------------
    def test_check_digit_matches_published_gstins(self):
        """The algorithm reproduces the last character of real GSTINs."""
        for gstin in ("33AAACC1206D1ZN", "27AAPFU0939F1ZV"):
            self.assertEqual(gstin_check_digit(gstin[:14]), gstin[14], gstin)

    # -- GSTIN ---------------------------------------------------------
    def test_valid_gstin_saves(self):
        partner = self.Partner.create({"name": "Valid", "drkds_in_gstin": "27AAPFU0939F1ZV"})
        self.assertEqual(partner.drkds_in_gstin, "27AAPFU0939F1ZV")

    def test_gstin_is_normalised(self):
        partner = self.Partner.create({"name": "Messy", "drkds_in_gstin": " 27aapfu0939f1zv "})
        self.assertEqual(partner.drkds_in_gstin, "27AAPFU0939F1ZV")

    def test_gstin_wrong_check_digit_refused(self):
        with self.assertRaises(ValidationError):
            self.Partner.create({"name": "Bad digit", "drkds_in_gstin": "27AAPFU0939F1ZA"})

    def test_gstin_wrong_structure_refused(self):
        with self.assertRaises(ValidationError):
            self.Partner.create({"name": "Too short", "drkds_in_gstin": "27AAPFU0939F"})

    def test_gstin_state_code_is_resolved(self):
        partner = self.Partner.create({"name": "MH", "drkds_in_gstin": "27AAPFU0939F1ZV"})
        self.assertEqual(partner.drkds_in_state_code_id.code, "27")
        self.assertEqual(partner.drkds_in_state_code_id.state_id, self.maharashtra)

    def test_gstin_state_mismatch_refused(self):
        """A Maharashtra GSTIN on a Gujarat address is refused."""
        with self.assertRaises(ValidationError):
            self.Partner.create({
                "name": "Wrong state",
                "drkds_in_gstin": "27AAPFU0939F1ZV",
                "country_id": self.india.id,
                "state_id": self.gujarat.id,
            })

    def test_gstin_state_match_accepted(self):
        partner = self.Partner.create({
            "name": "Right state",
            "drkds_in_gstin": "27AAPFU0939F1ZV",
            "country_id": self.india.id,
            "state_id": self.maharashtra.id,
        })
        self.assertTrue(partner.id)

    def test_gstin_pan_disagreement_refused(self):
        with self.assertRaises(ValidationError):
            self.Partner.create({
                "name": "Disagree",
                "drkds_in_gstin": "27AAPFU0939F1ZV",
                "drkds_in_pan": "ABCDE1234F",
            })

    def test_gstin_pan_agreement_accepted(self):
        partner = self.Partner.create({
            "name": "Agree",
            "drkds_in_gstin": "27AAPFU0939F1ZV",
            "drkds_in_pan": "AAPFU0939F",
        })
        self.assertTrue(partner.id)

    def test_duplicate_gstin_warns_but_saves(self):
        self.Partner.create({"name": "First", "drkds_in_gstin": "27AAPFU0939F1ZV"})
        second = self.Partner.create({"name": "Second", "drkds_in_gstin": "27AAPFU0939F1ZV"})
        self.assertTrue(second.id, "a duplicate GSTIN must not block the save")
        self.assertIn("First", second.drkds_in_gstin_warning)

    # -- PAN -----------------------------------------------------------
    def test_valid_pan_saves(self):
        partner = self.Partner.create({"name": "PAN", "drkds_in_pan": "ABCPD1234E"})
        self.assertEqual(partner.drkds_in_pan, "ABCPD1234E")

    def test_pan_bad_structure_refused(self):
        with self.assertRaises(ValidationError):
            self.Partner.create({"name": "Bad PAN", "drkds_in_pan": "AB1DE1234F"})

    def test_pan_bad_holder_type_refused(self):
        """The fourth character must be an issued holder-type letter."""
        with self.assertRaises(ValidationError):
            self.Partner.create({"name": "Bad type", "drkds_in_pan": "ABCXE1234F"})

    # -- IFSC ----------------------------------------------------------
    def test_valid_ifsc_saves(self):
        partner = self.Partner.create({"name": "Bank", "drkds_in_ifsc": "HDFC0001234"})
        self.assertEqual(partner.drkds_in_ifsc, "HDFC0001234")

    def test_ifsc_without_reserved_zero_refused(self):
        with self.assertRaises(ValidationError):
            self.Partner.create({"name": "Bad IFSC", "drkds_in_ifsc": "HDFC1001234"})

    # -- PIN -----------------------------------------------------------
    def test_valid_pin_saves(self):
        partner = self.Partner.create({
            "name": "Pin", "country_id": self.india.id, "zip": "400001",
        })
        self.assertEqual(partner.zip, "400001")

    def test_pin_starting_with_zero_refused(self):
        with self.assertRaises(ValidationError):
            self.Partner.create({
                "name": "Bad pin", "country_id": self.india.id, "zip": "040001",
            })

    def test_non_indian_zip_untouched(self):
        """A non-Indian address keeps whatever postal format it uses."""
        partner = self.Partner.create({
            "name": "UK", "country_id": self.env.ref("base.uk").id, "zip": "SW1A 1AA",
        })
        self.assertEqual(partner.zip, "SW1A 1AA")

    # -- blanks --------------------------------------------------------
    def test_all_identifiers_optional(self):
        partner = self.Partner.create({"name": "Nothing"})
        self.assertFalse(partner.drkds_in_gstin)
        self.assertFalse(partner.drkds_in_gstin_warning)
