from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestLabelTemplate(TransactionCase):
    """The size is the whole point of the module, so it is tested first."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Template = cls.env["drkds.lite.label.template"]

    def _template(self, **vals):
        return self.Template.create(dict({
            "name": "Roll 50 x 25",
            "applies_to": "product",
            "width_mm": 50,
            "height_mm": 25,
        }, **vals))

    # -- paper format --------------------------------------------------
    def test_paperformat_matches_declared_size(self):
        """A 50 x 25 mm template generates a 50 x 25 mm custom page."""
        template = self._template()
        paperformat = template.paperformat_id
        self.assertTrue(paperformat, "a paper format is generated on create")
        self.assertEqual(paperformat.format, "custom")
        self.assertEqual(paperformat.page_width, 50)
        self.assertEqual(paperformat.page_height, 25)
        self.assertEqual(paperformat.orientation, "Portrait")

    def test_paperformat_has_no_page_margins(self):
        """Margins live inside the page; wkhtmltopdf margins would eat the label."""
        template = self._template(margin_top=3.0)
        paperformat = template.paperformat_id
        self.assertEqual(
            (paperformat.margin_top, paperformat.margin_bottom,
             paperformat.margin_left, paperformat.margin_right),
            (0.0, 0.0, 0.0, 0.0),
        )
        self.assertTrue(paperformat.disable_shrinking, "smart shrinking would rescale the page")
        self.assertIn("3.0mm", template._page_style())

    def test_paperformat_follows_a_resize(self):
        """Changing the size rewrites the same paper format rather than orphaning it."""
        template = self._template()
        paperformat = template.paperformat_id
        template.write({"width_mm": 100, "height_mm": 150})
        self.assertEqual(template.paperformat_id, paperformat)
        self.assertEqual(paperformat.page_width, 100)
        self.assertEqual(paperformat.page_height, 150)

    def test_paperformat_is_removed_with_the_template(self):
        template = self._template()
        paperformat = template.paperformat_id
        template.unlink()
        self.assertFalse(paperformat.exists())

    def test_report_uses_the_template_paperformat(self):
        """The report action honours the template pinned in the context."""
        template = self._template()
        report = self.env.ref("drkds_label_designer_lite.action_report_drkds_label")
        chosen = report.with_context(
            drkds_label_template_id=template.id,
        ).get_paperformat()
        self.assertEqual(chosen, template.paperformat_id)
        self.assertNotEqual(report.get_paperformat(), template.paperformat_id)

    # -- refused sizes -------------------------------------------------
    def test_zero_size_is_refused(self):
        for vals in ({"width_mm": 0}, {"height_mm": 0}):
            with self.subTest(vals=vals), self.assertRaises(ValidationError):
                self._template(**vals)

    def test_negative_size_is_refused(self):
        for vals in ({"width_mm": -50}, {"height_mm": -25}):
            with self.subTest(vals=vals), self.assertRaises(ValidationError):
                self._template(**vals)

    def test_resize_to_zero_is_refused(self):
        template = self._template()
        with self.assertRaises(ValidationError):
            template.width_mm = 0

    def test_negative_margin_is_refused(self):
        with self.assertRaises(ValidationError):
            self._template(margin_left=-1.0)

    def test_margins_may_not_swallow_the_label(self):
        with self.assertRaises(ValidationError):
            self._template(margin_left=30.0, margin_right=30.0)

    # -- field paths ---------------------------------------------------
    def test_unknown_field_path_is_refused(self):
        template = self._template()
        with self.assertRaises(ValidationError):
            self.env["drkds.lite.label.template.line"].create({
                "template_id": template.id,
                "content_type": "field",
                "field_path": "no_such_field",
            })

    def test_path_through_a_non_relation_is_refused(self):
        template = self._template()
        with self.assertRaises(ValidationError):
            self.env["drkds.lite.label.template.line"].create({
                "template_id": template.id,
                "content_type": "field",
                "field_path": "default_code.name",
            })

    def test_dotted_path_through_a_relation_is_accepted(self):
        template = self._template(applies_to="lot")
        line = self.env["drkds.lite.label.template.line"].create({
            "template_id": template.id,
            "content_type": "field",
            "field_path": "product_id.default_code",
        })
        self.assertTrue(line.id)

    def test_shipped_templates_are_usable(self):
        """The two data templates install with a size and some lines."""
        for xml_id in (
            "drkds_label_designer_lite.label_template_product_50x25",
            "drkds_label_designer_lite.label_template_lot_50x25",
        ):
            template = self.env.ref(xml_id)
            self.assertEqual((template.width_mm, template.height_mm), (50, 25))
            self.assertTrue(template.line_ids)
            self.assertEqual(template.paperformat_id.page_width, 50)
