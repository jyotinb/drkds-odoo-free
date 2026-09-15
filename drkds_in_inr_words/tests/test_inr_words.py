from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestInrWords(TransactionCase):
    """The scale must follow the currency, never the user's interface language."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.inr = cls.env.ref("base.INR")
        cls.usd = cls.env.ref("base.USD")
        cls.company.write({
            "drkds_inr_words_enabled": True,
            "drkds_inr_words_connector": "and",
            "drkds_inr_words_suffix": "Only",
            "drkds_inr_words_show_zero_paise": False,
        })
        # Odoo ships these blank; pin them so the wording is deterministic.
        cls.inr.write({"currency_unit_label": False, "currency_subunit_label": False})
        # English (IN) is the language that already got the right words without
        # this module. It has to be activated before it can be used as a
        # context language at all.
        cls.en_in_available = bool(cls.env["res.lang"]._activate_lang("en_IN"))

    def words(self, amount, currency=None, lang="en_US"):
        currency = currency or self.inr
        return currency.with_context(lang=lang).amount_to_text(amount)

    # -- the required value table --------------------------------------
    def test_zero(self):
        self.assertEqual(self.words(0), "Rupees Zero Only")

    def test_one(self):
        self.assertEqual(self.words(1), "Rupees One Only")

    def test_ninety_nine(self):
        self.assertEqual(self.words(99), "Rupees Ninety-Nine Only")

    def test_hundred(self):
        self.assertEqual(self.words(100), "Rupees One Hundred Only")

    def test_thousand(self):
        self.assertEqual(self.words(1000), "Rupees One Thousand Only")

    def test_one_lakh_not_hundred_thousand(self):
        """The whole point: 10**5 is a lakh, on a database running en_US."""
        self.assertEqual(self.words(100000), "Rupees One Lakh Only")

    def test_one_crore_not_ten_million(self):
        self.assertEqual(self.words(10000000), "Rupees One Crore Only")

    def test_large_amount(self):
        words = self.words(1234567890)
        self.assertIn("Crore", words)
        self.assertIn("Lakh", words)
        self.assertNotIn("Million", words)
        self.assertNotIn("Billion", words)
        self.assertTrue(words.startswith("Rupees One Hundred And Twenty-Three Crore"), words)
        self.assertTrue(words.endswith("Only"), words)

    def test_amount_with_paise(self):
        self.assertEqual(self.words(500.50), "Rupees Five Hundred and Fifty Paise Only")

    def test_amount_with_zero_paise_is_short_by_default(self):
        self.assertEqual(self.words(500.00), "Rupees Five Hundred Only")

    def test_negative_amount(self):
        self.assertEqual(
            self.words(-1500.25),
            "Minus Rupees One Thousand Five Hundred and Twenty-Five Paise Only",
        )

    # -- the bug this module exists for --------------------------------
    def test_scale_is_the_same_in_every_interface_language(self):
        """A user on en_US and a user on en_IN must print the same rupee words."""
        if not self.en_in_available:  # pragma: no cover - en_IN ships with Odoo
            self.skipTest("the en_IN language is not available in this install")
        self.assertEqual(self.words(100000, lang="en_US"), self.words(100000, lang="en_IN"))

    def test_en_in_user_already_got_lakh_from_core(self):
        """Guard the premise from the other side: core is right in en_IN.

        This is why the module does not write its own converter. num2words
        already knows the Indian scale; Odoo simply asks it the wrong question
        for everyone who is not running this language.
        """
        if not self.en_in_available:  # pragma: no cover - en_IN ships with Odoo
            self.skipTest("the en_IN language is not available in this install")
        self.company.drkds_inr_words_enabled = False
        self.assertIn("Lakh", self.words(100000, lang="en_IN"))

    def test_core_would_have_got_it_wrong_in_en_us(self):
        """Guard the premise: with the feature off, core reads en_US as millions."""
        self.company.drkds_inr_words_enabled = False
        self.assertIn("Million", self.words(10000000, lang="en_US"))

    def test_disabling_restores_core_behaviour(self):
        self.company.drkds_inr_words_enabled = False
        words = self.words(100000)
        self.assertNotIn("Lakh", words)
        self.assertNotIn("Only", words)

    # -- other currencies are untouched --------------------------------
    def test_foreign_currency_is_left_to_core(self):
        """Core's sentence is returned verbatim: no suffix, no paise clause."""
        words = self.words(100000, currency=self.usd)
        self.assertIn("Thousand", words)
        self.assertFalse(words.endswith("Only"), words)

    def test_foreign_currency_is_unaffected_by_the_switch(self):
        before = self.words(100000, currency=self.usd)
        self.company.drkds_inr_words_enabled = False
        self.assertEqual(self.words(100000, currency=self.usd), before)

    def test_foreign_currency_is_never_read_in_lakh(self):
        self.assertNotIn("Lakh", self.words(100000, currency=self.usd))

    # -- paise handling ------------------------------------------------
    def test_paise_are_rounded_to_the_currency_decimal_places(self):
        """0.999 rupees is one rupee, not "Zero and Ninety-Nine Paise"."""
        self.assertEqual(self.words(0.999), "Rupees One Only")

    def test_single_paise(self):
        self.assertEqual(self.words(7.01), "Rupees Seven and One Paise Only")

    def test_zero_paise_can_be_spelled_out(self):
        self.company.drkds_inr_words_show_zero_paise = True
        self.assertEqual(self.words(500.00), "Rupees Five Hundred and Zero Paise Only")

    # -- configurable wording ------------------------------------------
    def test_suffix_is_configurable(self):
        self.company.drkds_inr_words_suffix = "Only (E. & O.E.)"
        self.assertEqual(self.words(100), "Rupees One Hundred Only (E. & O.E.)")

    def test_suffix_can_be_removed(self):
        self.company.drkds_inr_words_suffix = False
        self.assertEqual(self.words(100), "Rupees One Hundred")

    def test_connector_is_configurable(self):
        self.company.drkds_inr_words_connector = "Point"
        self.assertEqual(self.words(500.50), "Rupees Five Hundred Point Fifty Paise Only")

    def test_empty_connector_joins_with_a_single_space(self):
        self.company.drkds_inr_words_connector = False
        words = self.words(500.50)
        self.assertEqual(words, "Rupees Five Hundred Fifty Paise Only")
        self.assertNotIn("  ", words)

    def test_currency_labels_override_the_defaults(self):
        self.inr.write({
            "currency_unit_label": "Rupee",
            "currency_subunit_label": "Paisa",
        })
        self.assertEqual(self.words(2.05), "Rupee Two and Five Paisa Only")

    def test_no_list_commas_survive_in_the_sentence(self):
        """num2words separates Indian groups with commas; a legal sentence must not."""
        self.assertNotIn(",", self.words(1234567))

    # -- the fields on the document ------------------------------------
    def _invoice(self, price_unit, tax=None):
        return self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.env["res.partner"].create({"name": "Words Co"}).id,
            "currency_id": self.inr.id,
            "invoice_line_ids": [(0, 0, {
                "name": "Consulting",
                "quantity": 1,
                "price_unit": price_unit,
                "tax_ids": [(6, 0, tax.ids)] if tax else [(5, 0, 0)],
            })],
        })

    def test_core_total_in_words_field_now_reads_indian(self):
        """Core's own field is the one that reaches the PDF, so it must be right."""
        invoice = self._invoice(150000.00)
        self.assertEqual(invoice.amount_total, 150000.00)
        self.assertEqual(invoice.amount_total_words, "Rupees One Lakh Fifty Thousand Only")

    def test_tax_amount_in_words(self):
        tax = self.env["account.tax"].create({
            "name": "GST 18%",
            "amount_type": "percent",
            "amount": 18.0,
            "type_tax_use": "sale",
        })
        invoice = self._invoice(1000000.00, tax=tax)
        self.assertEqual(invoice.amount_tax, 180000.00)
        self.assertEqual(
            invoice.drkds_tax_amount_in_words,
            "Rupees One Lakh Eighty Thousand Only",
        )

    def test_tax_amount_in_words_follows_the_total(self):
        invoice = self._invoice(150000.00)
        self.assertEqual(invoice.drkds_tax_amount_in_words, "Rupees Zero Only")

    def test_tax_amount_in_words_is_not_stored(self):
        field = self.env["account.move"]._fields["drkds_tax_amount_in_words"]
        self.assertFalse(field.store)
