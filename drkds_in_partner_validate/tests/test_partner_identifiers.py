from odoo.addons.base_vat.models.res_partner import ResPartner as BaseVatPartner
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

from ..models.res_partner import GSTIN_NORMAL_RE, gstin_check_digit

#: Two published, real GSTINs used throughout.
MH_GSTIN = "27AAPFU0939F1ZV"
TN_GSTIN = "33AAACC1206D1ZN"

#: One sample per shape ``base_vat.check_vat_in`` accepts.
CORE_ACCEPTED_FORMS = {
    "normal/composite/casual": MH_GSTIN,
    "UN or ON body": "0700ABC12345UNZ",
    "NRI": "0700ABC12345NR9",
    "TDS": "27ABCDE1234F1D5",
    "TCS": "27ABCDE1234F1C5",
}

#: The EDI test credential l10n_in short-circuits on.
L10N_IN_TEST_GST_NUMBER = "36AABCT1332L011"


@tagged("post_install", "-at_install")
class TestPartnerIdentifiers(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.india = cls.env.ref("base.in")
        cls.maharashtra = cls.env.ref("base.state_in_mh")
        cls.gujarat = cls.env.ref("base.state_in_gj")

    def _indian(self, name, **vals):
        return self.Partner.create(dict(vals, name=name, country_id=self.india.id))

    # -- check digit ---------------------------------------------------
    def test_check_digit_matches_published_gstins(self):
        """The algorithm reproduces the last character of real GSTINs."""
        for gstin in (TN_GSTIN, MH_GSTIN):
            self.assertEqual(gstin_check_digit(gstin[:14]), gstin[14], gstin)

    # -- check_vat_in override ----------------------------------------
    def test_core_accepted_forms_are_not_refused(self):
        """Every shape core accepts still passes through this override."""
        for label, gstin in CORE_ACCEPTED_FORMS.items():
            with self.subTest(form=label):
                self.assertTrue(self.Partner.check_vat_in(gstin), label)

    def test_exotic_forms_skip_the_checksum(self):
        """UN body and TDS numbers are accepted on core's regex alone."""
        for gstin in ("0700ABC12345UNZ", "27ABCDE1234F1D5"):
            with self.subTest(gstin=gstin):
                self.assertFalse(
                    GSTIN_NORMAL_RE.match(gstin),
                    "an exotic form must never reach the check digit",
                )
                self.assertTrue(self.Partner.check_vat_in(gstin))

    def test_corrupted_check_digit_is_refused(self):
        """A normal GSTIN core would accept is refused on its check digit."""
        corrupted = MH_GSTIN[:14] + "A"
        self.assertNotEqual(corrupted, MH_GSTIN)
        self.assertTrue(
            BaseVatPartner.check_vat_in(self.Partner, corrupted),
            "core accepts the structure, so this test is testing our addition",
        )
        self.assertFalse(self.Partner.check_vat_in(corrupted))

    def test_structurally_invalid_still_refused(self):
        for bad in ("27AAPFU0939F", "", "hello"):
            with self.subTest(vat=bad):
                self.assertFalse(self.Partner.check_vat_in(bad))

    def test_l10n_in_test_gst_number_is_not_checksum_tested(self):
        """l10n_in's EDI credential survives whatever the load order is.

        l10n_in returns True for it before calling super(), and it does not
        match the ordinary form, so this override never applies a check digit
        to it from the other side of the MRO either.
        """
        self.assertFalse(GSTIN_NORMAL_RE.match(L10N_IN_TEST_GST_NUMBER))
        installed = self.env["ir.module.module"].search(
            [("name", "=", "l10n_in"), ("state", "=", "installed")]
        )
        if installed:
            self.assertTrue(self.Partner.check_vat_in(L10N_IN_TEST_GST_NUMBER))
        else:
            # Without l10n_in nobody claims it is valid, and that is core's call.
            self.assertFalse(self.Partner.check_vat_in(L10N_IN_TEST_GST_NUMBER))

    # -- GSTIN on the vat field ---------------------------------------
    def test_valid_gstin_saves(self):
        partner = self._indian("Valid", vat=MH_GSTIN, state_id=self.maharashtra.id)
        self.assertEqual(partner.vat, MH_GSTIN)

    def test_second_published_gstin_saves(self):
        partner = self._indian("Valid TN", vat=TN_GSTIN)
        self.assertEqual(partner.vat, TN_GSTIN)

    def test_gstin_is_normalised(self):
        partner = self._indian("Messy", vat=" 27aapfu0939f1zv ")
        self.assertEqual(partner.vat, MH_GSTIN)

    def test_gstin_wrong_check_digit_refused(self):
        with self.assertRaises(ValidationError):
            self._indian("Bad digit", vat="27AAPFU0939F1ZA")

    def test_gstin_wrong_check_digit_refused_without_country(self):
        """A contact with no country still gets the check digit test."""
        with self.assertRaises(ValidationError):
            self.Partner.create({"name": "No country", "vat": "27AAPFU0939F1ZA"})

    def test_gstin_wrong_structure_refused(self):
        """base_vat's own constraint stays in force on an Indian contact."""
        with self.assertRaises(ValidationError):
            self._indian("Too short", vat="27AAPFU0939F")

    def test_non_indian_vat_untouched(self):
        """A foreign tax id is neither reshaped nor checksum tested."""
        partner = self.Partner.create({
            "name": "Foreign",
            "country_id": self.env.ref("base.uk").id,
            "vat": "GB123456782",
        })
        self.assertEqual(partner.vat, "GB123456782")
        self.assertFalse(partner.drkds_in_state_code_id)

    def test_gstin_state_code_is_resolved(self):
        partner = self._indian("MH", vat=MH_GSTIN)
        self.assertEqual(partner.drkds_in_state_code_id.code, "27")
        self.assertEqual(partner.drkds_in_state_code_id.state_id, self.maharashtra)

    def test_gstin_state_mismatch_refused(self):
        """A Maharashtra GSTIN on a Gujarat address is refused."""
        with self.assertRaises(ValidationError):
            self._indian("Wrong state", vat=MH_GSTIN, state_id=self.gujarat.id)

    def test_gstin_state_match_accepted(self):
        partner = self._indian("Right state", vat=MH_GSTIN, state_id=self.maharashtra.id)
        self.assertTrue(partner.id)

    def test_gstin_pan_disagreement_refused(self):
        with self.assertRaises(ValidationError):
            self._indian("Disagree", vat=MH_GSTIN, drkds_in_pan="ABCDE1234F")

    def test_gstin_pan_agreement_accepted(self):
        partner = self._indian("Agree", vat=MH_GSTIN, drkds_in_pan="AAPFU0939F")
        self.assertTrue(partner.id)

    def test_duplicate_gstin_warns_but_saves(self):
        self._indian("First", vat=MH_GSTIN)
        second = self._indian("Second", vat=MH_GSTIN)
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
        partner = self._indian("Pin", zip="400001")
        self.assertEqual(partner.zip, "400001")

    def test_pin_starting_with_zero_refused(self):
        with self.assertRaises(ValidationError):
            self._indian("Bad pin", zip="040001")

    def test_non_indian_zip_untouched(self):
        """A non-Indian address keeps whatever postal format it uses."""
        partner = self.Partner.create({
            "name": "UK", "country_id": self.env.ref("base.uk").id, "zip": "SW1A 1AA",
        })
        self.assertEqual(partner.zip, "SW1A 1AA")

    # -- blanks --------------------------------------------------------
    def test_all_identifiers_optional(self):
        partner = self.Partner.create({"name": "Nothing"})
        self.assertFalse(partner.vat)
        self.assertFalse(partner.drkds_in_pan)
        self.assertFalse(partner.drkds_in_state_code_id)
        self.assertFalse(partner.drkds_in_gstin_warning)
