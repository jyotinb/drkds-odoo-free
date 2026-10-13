from random import randint

from odoo import fields, models


class DrkdsDocumentTag(models.Model):
    """A coloured label a document can carry any number of."""

    _name = "drkds.document.tag"
    _description = "Document Tag"
    _order = "name"

    def _default_color(self):
        # Colour 0 means "no colour": the Kanban card hides such tags.
        return randint(1, 11)

    name = fields.Char(required=True, translate=True)
    color = fields.Integer(default=_default_color)
    active = fields.Boolean(default=True)

    _name_uniq = models.Constraint("unique(name)", "A tag with this name already exists.")
