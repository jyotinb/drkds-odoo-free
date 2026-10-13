from odoo import fields, models


class DrkdsDocumentTag(models.Model):
    """A coloured label a document can carry any number of."""

    _name = "drkds.document.tag"
    _description = "Document Tag"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    color = fields.Integer(default=0)
    active = fields.Boolean(default=True)

    _name_uniq = models.Constraint("unique(name)", "A tag with this name already exists.")
