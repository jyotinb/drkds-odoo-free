from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

#: The record types a label template can be attached to, and the model each
#: one prints. Kept as a plain map so the selection, the model lookup and the
#: wizard domain can never drift apart.
APPLIES_TO_MODEL = {
    "product": "product.product",
    "lot": "stock.lot",
    "package": "stock.package",
    "picking": "stock.picking",
}


class DrkdsLabelTemplate(models.Model):
    """A label of a stated physical size, with a declarative list of what prints on it.

    The point of the model is the *size*. Odoo's own label wizard offers a small
    set of fixed sheet layouts on A4 plus one fixed Dymo format; roll stock of an
    arbitrary size is not reachable from it. Every template here owns a generated
    ``report.paperformat`` whose page is exactly the declared millimetres, so a
    50 x 25 mm label is produced as a 50 x 25 mm page rather than as a small
    rectangle centred on A4.
    """

    _name = "drkds.label.template"
    _description = "Label Template"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    applies_to = fields.Selection(
        [
            ("product", "Product"),
            ("lot", "Lot / Serial Number"),
            ("package", "Package"),
            ("picking", "Transfer"),
        ],
        string="Applies To",
        required=True,
        default="product",
        help="Which kind of record this label prints. It decides the model that "
        "field paths on the lines are resolved against.",
    )
    model_name = fields.Char(
        string="Technical Model", compute="_compute_model_name", store=True,
    )

    width_mm = fields.Integer(
        string="Width (mm)", required=True, default=50,
        help="Physical width of one label, in millimetres. This becomes the page "
        "width of the generated paper format.",
    )
    height_mm = fields.Integer(
        string="Height (mm)", required=True, default=25,
        help="Physical height of one label, in millimetres.",
    )
    margin_top = fields.Float(string="Top Margin (mm)", default=1.0)
    margin_bottom = fields.Float(string="Bottom Margin (mm)", default=1.0)
    margin_left = fields.Float(string="Left Margin (mm)", default=1.0)
    margin_right = fields.Float(string="Right Margin (mm)", default=1.0)

    line_ids = fields.One2many(
        "drkds.label.template.line", "template_id", string="Lines", copy=True,
    )
    paperformat_id = fields.Many2one(
        "report.paperformat", string="Paper Format", readonly=True, copy=False, ondelete="set null",
        help="Generated from the width and height above. Do not edit it by hand; "
        "it is rewritten whenever the size changes.",
    )
    show_border = fields.Boolean(
        string="Print Outline", default=False,
        help="Draw a thin rectangle around the label. Useful while calibrating a "
        "printer, normally switched off for production.",
    )

    _name_uniq = models.Constraint(
        "unique(name)",
        "A label template with this name already exists.",
    )

    # ------------------------------------------------------------------
    # Compute / constraints
    # ------------------------------------------------------------------
    @api.depends("applies_to")
    def _compute_model_name(self):
        for template in self:
            template.model_name = APPLIES_TO_MODEL.get(template.applies_to, False)

    @api.constrains("width_mm", "height_mm")
    def _check_dimensions(self):
        """A label with a zero or negative side cannot produce a page."""
        for template in self:
            if template.width_mm <= 0 or template.height_mm <= 0:
                raise ValidationError(
                    _(
                        "Label %(name)s must have a width and a height greater than "
                        "zero millimetres (got %(width)s x %(height)s).",
                        name=template.name or "",
                        width=template.width_mm,
                        height=template.height_mm,
                    )
                )

    @api.constrains("margin_top", "margin_bottom", "margin_left", "margin_right",
                    "width_mm", "height_mm")
    def _check_margins(self):
        """Margins must be positive and must leave something to print on."""
        for template in self:
            margins = (
                template.margin_top, template.margin_bottom,
                template.margin_left, template.margin_right,
            )
            if any(margin < 0 for margin in margins):
                raise ValidationError(
                    _("Label %s cannot have a negative margin.", template.name or "")
                )
            if template.margin_left + template.margin_right >= template.width_mm:
                raise ValidationError(
                    _("The left and right margins of %s leave no printable width.",
                      template.name or "")
                )
            if template.margin_top + template.margin_bottom >= template.height_mm:
                raise ValidationError(
                    _("The top and bottom margins of %s leave no printable height.",
                      template.name or "")
                )

    # ------------------------------------------------------------------
    # Paper format
    # ------------------------------------------------------------------
    def _paperformat_values(self):
        """The paper format that reproduces this label at its physical size.

        Margins are zero on the paper format itself and applied inside the page
        instead: wkhtmltopdf treats page margins as unprintable area, and on a
        50 mm roll every millimetre given away there is a millimetre the label
        loses. ``disable_shrinking`` stops the smart-shrink pass, which would
        otherwise rescale a small page and defeat the whole exercise.
        """
        self.ensure_one()
        return {
            "name": _("Label %s (%smm x %smm)", self.name, self.width_mm, self.height_mm),
            "format": "custom",
            "page_width": self.width_mm,
            "page_height": self.height_mm,
            "orientation": "Portrait",
            "margin_top": 0.0,
            "margin_bottom": 0.0,
            "margin_left": 0.0,
            "margin_right": 0.0,
            "header_line": False,
            "header_spacing": 0,
            "disable_shrinking": True,
            "dpi": 96,
        }

    def _sync_paperformat(self):
        """Create or refresh the paper format owned by each template."""
        for template in self:
            values = template._paperformat_values()
            if template.paperformat_id:
                template.paperformat_id.write(values)
            else:
                template.paperformat_id = self.env["report.paperformat"].create(values)
        return True

    @api.model_create_multi
    def create(self, vals_list):
        templates = super().create(vals_list)
        templates._sync_paperformat()
        return templates

    def write(self, vals):
        result = super().write(vals)
        if {"name", "width_mm", "height_mm"} & set(vals):
            self._sync_paperformat()
        return result

    def unlink(self):
        paperformats = self.paperformat_id
        result = super().unlink()
        paperformats.unlink()
        return result

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def _page_style(self):
        """Inline style of one label block, in millimetres."""
        self.ensure_one()
        style = (
            f"width:{self.width_mm}mm;height:{self.height_mm}mm;"
            f"padding:{self.margin_top}mm {self.margin_right}mm "
            f"{self.margin_bottom}mm {self.margin_left}mm;"
            "box-sizing:border-box;overflow:hidden;"
        )
        if self.show_border:
            style += "outline:0.2mm solid #000;outline-offset:-0.2mm;"
        return style

    def _render_cells(self, record):
        """Return the printable cells for one record, in line order."""
        self.ensure_one()
        cells = []
        for line in self.line_ids.sorted("sequence"):
            cell = line._render_cell(record)
            if cell:
                cells.append(cell)
        return cells

    def _check_record_model(self, records):
        """Refuse to print a template against the wrong kind of record."""
        self.ensure_one()
        if records and records._name != self.model_name:
            raise ValidationError(
                _(
                    "Label %(name)s prints %(expected)s records, not %(got)s.",
                    name=self.name, expected=self.model_name, got=records._name,
                )
            )
        return True
