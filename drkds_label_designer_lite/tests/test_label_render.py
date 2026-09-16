import unittest

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


def _barcode_backend_available():
    """Can reportlab actually rasterise a barcode on this host?

    Building the Drawing succeeds without a renderPM backend; only turning it
    into a PNG fails. Without ``rlPyCairo`` or ``_rl_renderPM`` no barcode
    renders anywhere in Odoo, core's own product labels included, so the tests
    that need a real image skip rather than report a fault in this module.
    """
    try:
        from reportlab.graphics.barcode import createBarcodeDrawing
        createBarcodeDrawing("Code128", value="123456", format="png").asString("png")
    except Exception:
        return False
    return True


BARCODE_BACKEND = _barcode_backend_available()

#: Host gap, not a fault in this module: without one of these backends no
#: barcode renders anywhere in Odoo, core's own product labels included.
NO_BACKEND_REASON = (
    "reportlab cannot rasterise a barcode on this host: neither rlPyCairo nor "
    "_rl_renderPM is installed. This is a host gap, not a module fault - no "
    "barcode renders anywhere in Odoo without one of them."
)


@tagged("post_install", "-at_install")
class TestLabelRender(TransactionCase):
    """What lands on the label, and how many of them come out."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create({
            "name": "Turmeric Powder 500g",
            "default_code": "TUR-500",
            "barcode": "8901234567894",
            "is_storable": True,
        })
        cls.template = cls.env["drkds.lite.label.template"].create({
            "name": "Render test 50 x 25",
            "applies_to": "product",
            "width_mm": 50,
            "height_mm": 25,
            "line_ids": [
                (0, 0, {
                    "sequence": 10,
                    "content_type": "field",
                    "field_path": "name",
                    "bold": True,
                }),
            ],
        })

    def _render(self, records, quantity=1, template=None):
        template = template or self.template
        data = {
            "template_id": template.id,
            "res_model": records._name,
            "res_ids": records.ids,
            "quantity": quantity,
        }
        html, _dummy = self.env["ir.actions.report"].with_context(
            drkds_label_template_id=template.id,
        )._render_qweb_html("drkds_label_designer_lite.report_drkds_label", template.ids, data=data)
        return html.decode() if isinstance(html, bytes) else html

    # -- chosen fields -------------------------------------------------
    def test_chosen_fields_appear(self):
        html = self._render(self.product)
        self.assertIn("Turmeric Powder 500g", html)

    def test_unchosen_fields_do_not_appear(self):
        """The internal reference is on the product but not on this label."""
        html = self._render(self.product)
        self.assertNotIn("TUR-500", html)

    def test_adding_a_line_adds_its_value(self):
        self.env["drkds.lite.label.template.line"].create({
            "template_id": self.template.id,
            "sequence": 30,
            "content_type": "field",
            "field_path": "default_code",
            "prefix": "Ref ",
        })
        html = self._render(self.product)
        self.assertIn("Ref TUR-500", html)

    def test_fixed_text_and_formatting(self):
        self.env["drkds.lite.label.template.line"].create({
            "template_id": self.template.id,
            "sequence": 40,
            "content_type": "text",
            "text": "Best before 6 months",
            "font_size_pt": 5.0,
            "align": "right",
        })
        html = self._render(self.product)
        self.assertIn("Best before 6 months", html)
        self.assertIn("font-size:5.0pt", html)
        self.assertIn("text-align:right", html)

    def test_empty_value_drops_its_line(self):
        """A product with no reference must not leave a blank row behind."""
        self.env["drkds.lite.label.template.line"].create({
            "template_id": self.template.id,
            "sequence": 30,
            "content_type": "field",
            "field_path": "default_code",
            "prefix": "Ref ",
            "hide_if_empty": True,
        })
        blank = self.env["product.product"].create({
            "name": "Unreferenced item", "barcode": "8901234567900",
        })
        self.assertNotIn("Ref ", self._render(blank))

    # -- barcode -------------------------------------------------------
    def _add_barcode_line(self):
        return self.env["drkds.lite.label.template.line"].create({
            "template_id": self.template.id,
            "sequence": 50,
            "content_type": "barcode",
            "field_path": "barcode",
            "barcode_symbology": "Code128",
        })

    @unittest.skipUnless(BARCODE_BACKEND, NO_BACKEND_REASON)
    def test_barcode_renders_as_an_image(self):
        self._add_barcode_line()
        html = self._render(self.product)
        self.assertIn("data:image/png;base64,", html,
                      "the barcode widget should emit an inline PNG")
        self.assertIn("8901234567894", html, "the value prints under the bars")

    @unittest.skipUnless(BARCODE_BACKEND, NO_BACKEND_REASON)
    def test_barcode_uses_odoo_barcode_engine(self):
        """No new library: the same entry point core's own labels use."""
        image = self.env["ir.actions.report"].barcode("Code128", "8901234567894")
        self.assertTrue(image)

    def test_a_barcode_line_is_configured_not_drawn_by_this_module(self):
        """The line carries the symbology; the drawing is Odoo's own engine."""
        line = self._add_barcode_line()
        cell = line._render_cell(self.product)
        self.assertEqual(cell["kind"], "barcode")
        self.assertEqual(cell["value"], "8901234567894")
        self.assertEqual(cell["options"]["widget"], "barcode")
        self.assertEqual(cell["options"]["symbology"], "Code128")

    # -- quantity ------------------------------------------------------
    def test_quantity_repeats_the_label(self):
        once = self._render(self.product, quantity=1)
        thrice = self._render(self.product, quantity=3)
        self.assertEqual(once.count('class="o_drkds_label"'), 1)
        self.assertEqual(thrice.count('class="o_drkds_label"'), 3)
        self.assertEqual(thrice.count("Turmeric Powder 500g"), 3)

    def test_several_records_each_get_their_copies(self):
        other = self.env["product.product"].create({
            "name": "Chilli Powder 500g", "barcode": "8901234567917",
        })
        html = self._render(self.product | other, quantity=2)
        self.assertEqual(html.count("Turmeric Powder 500g"), 2)
        self.assertEqual(html.count("Chilli Powder 500g"), 2)

    def test_page_size_is_in_the_rendered_markup(self):
        html = self._render(self.product)
        self.assertIn("width:50mm;height:25mm", html)

    # -- guards --------------------------------------------------------
    def test_wrong_record_type_is_refused(self):
        lot_template = self.env["drkds.lite.label.template"].create({
            "name": "Lot only", "applies_to": "lot", "width_mm": 40, "height_mm": 20,
        })
        with self.assertRaises(Exception):
            self._render(self.product, template=lot_template)

    def test_nothing_to_print_is_refused(self):
        with self.assertRaises(UserError):
            self._render(self.env["product.product"])


@tagged("post_install", "-at_install")
class TestLabelPrintWizard(TransactionCase):
    """Starting the wizard from a record."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = cls.env.ref("drkds_label_designer_lite.label_template_product_50x25")
        cls.product = cls.env["product.product"].create({
            "name": "Mustard Oil 1L", "default_code": "MUS-1L", "barcode": "8901234567924",
        })

    def _wizard(self, records, **vals):
        return self.env["drkds.lite.label.print"].with_context(
            active_model=records._name, active_ids=records.ids,
        ).create(vals) if vals else self.env["drkds.lite.label.print"].with_context(
            active_model=records._name, active_ids=records.ids,
        ).create({})

    def test_defaults_from_a_product(self):
        wizard = self._wizard(self.product)
        self.assertEqual(wizard.applies_to, "product")
        self.assertEqual(wizard.res_model, "product.product")
        self.assertEqual(wizard._record_ids(), self.product.ids)
        self.assertEqual(wizard.record_count, 1)

    def test_a_product_template_resolves_to_its_variants(self):
        wizard = self._wizard(self.product.product_tmpl_id)
        self.assertEqual(wizard.res_model, "product.product")
        self.assertEqual(wizard._record_ids(), self.product.ids)

    def test_print_returns_a_report_action_carrying_the_template(self):
        wizard = self._wizard(self.product)
        wizard.write({"template_id": self.template.id, "quantity": 4})
        action = wizard.action_print()
        self.assertEqual(action["type"], "ir.actions.report")
        self.assertEqual(action["data"]["quantity"], 4)
        self.assertEqual(action["data"]["res_ids"], self.product.ids)
        self.assertEqual(action["context"]["drkds_label_template_id"], self.template.id)

    def test_zero_copies_is_refused(self):
        wizard = self._wizard(self.product)
        wizard.write({"template_id": self.template.id, "quantity": 0})
        with self.assertRaises(UserError):
            wizard.action_print()

    def test_an_unsupported_model_is_refused(self):
        with self.assertRaises(UserError):
            self.env["drkds.lite.label.print"].with_context(
                active_model="res.users", active_ids=[self.env.uid],
            ).create({})
