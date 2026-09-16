from odoo import fields, models


class DrkdsKbTag(models.Model):
    """A free-form label on an article.

    Sections answer "where does this live"; tags answer "what else is like
    this", which is a different question and deliberately not a hierarchy.
    """

    _name = "drkds.lite.kb.tag"
    _description = "Knowledge Base Tag"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    color = fields.Integer(string="Colour Index", default=0)
    article_ids = fields.Many2many(
        "drkds.lite.kb.article", "drkds_lite_kb_article_tag_rel", "tag_id", "article_id",
        string="Articles",
    )

    _name_uniq = models.Constraint(
        "unique(name)",
        "A tag with this name already exists.",
    )
