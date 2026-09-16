from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import format_amount, format_date, format_datetime
from odoo.tools.image import image_data_uri


class DrkdsLabelTemplateLine(models.Model):
    """One printed row of a label.

    The layout is deliberately a list, not a canvas. A line states what it
    prints, how big it is and how it is aligned; the lines stack down the label
    in sequence order. That covers the formats roll-label users actually ask for
    - a name, a lot number, an expiry date, a price, a barcode - without an
    editor no one would maintain.
    """

    _name = "drkds.lite.label.template.line"
    _description = "Label Template Line"
    _order = "sequence, id"

    template_id = fields.Many2one(
        "drkds.lite.label.template", string="Label Template", required=True, ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    content_type = fields.Selection(
        [
            ("field", "Field Value"),
            ("text", "Fixed Text"),
            ("barcode", "Barcode"),
            ("logo", "Company Logo"),
        ],
        string="Content",
        required=True,
        default="field",
    )
    field_path = fields.Char(
        string="Field Path",
        help="Dotted path read from the printed record, for example "
        "'name', 'default_code', 'barcode', 'product_id.name' or "
        "'expiration_date'. Any field the record carries can be used, including "
        "a field added by another module or by Studio.",
    )
    text = fields.Char(
        string="Text", translate=True,
        help="Printed as-is for a Fixed Text line.",
    )
    prefix = fields.Char(
        translate=True,
        help="Printed immediately before the value, for example 'Exp: '.",
    )
    suffix = fields.Char(translate=True)
    barcode_symbology = fields.Selection(
        [
            ("auto", "Automatic"),
            ("Code128", "Code 128"),
            ("EAN13", "EAN-13"),
            ("EAN8", "EAN-8"),
            ("QR", "QR Code"),
        ],
        string="Symbology",
        default="auto",
        help="Rendered by Odoo's own barcode engine. No extra library is used.",
    )
    barcode_height_mm = fields.Float(string="Barcode Height (mm)", default=8.0)
    show_barcode_value = fields.Boolean(
        string="Print Value Below", default=True,
        help="Print the barcode's text underneath the bars.",
    )
    image_height_mm = fields.Float(string="Image Height (mm)", default=8.0)
    font_size_pt = fields.Float(string="Font Size (pt)", default=8.0)
    bold = fields.Boolean()
    align = fields.Selection(
        [("left", "Left"), ("center", "Centre"), ("right", "Right")],
        required=True, default="left",
    )
    hide_if_empty = fields.Boolean(
        string="Hide If Empty", default=True,
        help="Drop the line entirely when the record has no value for it, so the "
        "rest of the label moves up instead of leaving a gap.",
    )

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains("content_type", "field_path", "text", "template_id")
    def _check_content(self):
        for line in self:
            if line.content_type in ("field", "barcode"):
                if not line.field_path:
                    raise ValidationError(
                        _("A %s line needs a field path.", line.content_type)
                    )
                line._check_field_path()
            elif line.content_type == "text" and not line.text:
                raise ValidationError(_("A fixed text line needs some text."))

    @api.constrains("font_size_pt", "barcode_height_mm", "image_height_mm")
    def _check_sizes(self):
        for line in self:
            if line.font_size_pt <= 0:
                raise ValidationError(_("The font size must be greater than zero."))
            if line.content_type == "barcode" and line.barcode_height_mm <= 0:
                raise ValidationError(_("The barcode height must be greater than zero."))
            if line.content_type == "logo" and line.image_height_mm <= 0:
                raise ValidationError(_("The image height must be greater than zero."))

    def _check_field_path(self):
        """Walk the dotted path across the model tree and fail loudly if it breaks."""
        self.ensure_one()
        model_name = self.template_id.model_name
        if not model_name or model_name not in self.env:
            return True
        model = self.env[model_name]
        parts = (self.field_path or "").split(".")
        for index, part in enumerate(parts):
            field = model._fields.get(part)
            if field is None:
                raise ValidationError(
                    _(
                        "%(model)s has no field %(field)s (in path %(path)s).",
                        model=model._name, field=part, path=self.field_path,
                    )
                )
            if index < len(parts) - 1:
                if not field.relational:
                    raise ValidationError(
                        _(
                            "%(field)s is not a relation, so nothing can follow it in "
                            "the path %(path)s.",
                            field=part, path=self.field_path,
                        )
                    )
                model = self.env[field.comodel_name]
        return True

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def _resolve(self, record):
        """Return ``(record, field_name)`` for the last hop of the field path."""
        self.ensure_one()
        parts = (self.field_path or "").split(".")
        for part in parts[:-1]:
            record = record[part][:1]
            if not record:
                return record, parts[-1]
        return record, parts[-1]

    def _format_value(self, record, field_name):
        """Turn a raw field value into the string that belongs on a label."""
        self.ensure_one()
        if not record or field_name not in record._fields:
            return ""
        field = record._fields[field_name]
        value = record[field_name]
        if value is False or value is None or value == "":
            return ""
        if field.type == "boolean":
            return _("Yes") if value else _("No")
        if field.type == "selection":
            return dict(field._description_selection(self.env)).get(value, str(value))
        if field.type in ("many2one", "many2many", "one2many"):
            return ", ".join(value.mapped("display_name"))
        if field.type == "date":
            return format_date(self.env, value)
        if field.type == "datetime":
            return format_datetime(self.env, value)
        if field.type == "monetary":
            currency = record[field.get_currency_field(record)] if field.get_currency_field(record) else None
            if currency:
                return format_amount(self.env, value, currency)
            return str(value)
        if field.type == "binary":
            return ""
        return str(value)

    def _text_style(self):
        self.ensure_one()
        style = (
            f"font-size:{self.font_size_pt}pt;"
            f"text-align:{'center' if self.align == 'center' else self.align};"
            "line-height:1.1;width:100%;"
        )
        if self.bold:
            style += "font-weight:bold;"
        return style

    def _render_cell(self, record):
        """Return a dict the QWeb template can print, or ``False`` to skip the line."""
        self.ensure_one()
        style = self._text_style()
        if self.content_type == "text":
            return {
                "kind": "text",
                "value": self.text or "",
                "style": style,
            }
        if self.content_type == "logo":
            logo = record.company_id.logo if "company_id" in record._fields and record.company_id else self.env.company.logo
            if not logo:
                return False
            return {
                "kind": "image",
                "src": image_data_uri(logo),
                "style": style,
                "img_style": f"height:{self.image_height_mm}mm;max-width:100%;",
            }

        target, field_name = self._resolve(record)
        value = self._format_value(target, field_name)
        if not value and self.hide_if_empty:
            return False

        if self.content_type == "barcode":
            return {
                "kind": "barcode",
                "value": value,
                "style": style,
                "show_value": self.show_barcode_value,
                "options": {
                    "widget": "barcode",
                    "symbology": self.barcode_symbology or "auto",
                    "quiet": 0,
                    "img_style": f"height:{self.barcode_height_mm}mm;max-width:100%;",
                },
            }
        return {
            "kind": "text",
            "value": f"{self.prefix or ''}{value}{self.suffix or ''}",
            "style": style,
        }
