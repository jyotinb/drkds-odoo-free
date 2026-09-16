from odoo import fields, models


class DrkdsKbFavourite(models.Model):
    """One user's bookmark on one article.

    Deliberately a separate model rather than a many2many on the article: a
    reader must be able to bookmark without being granted write access to the
    article itself.
    """

    _name = "drkds.kb.favourite"
    _description = "Knowledge Base Bookmark"
    _order = "create_date desc"

    user_id = fields.Many2one(
        "res.users", string="User", required=True, index=True, ondelete="cascade",
        default=lambda self: self.env.user,
    )
    article_id = fields.Many2one(
        "drkds.lite.kb.article", string="Article", required=True, index=True,
        ondelete="cascade",
    )

    _user_article_uniq = models.Constraint(
        "unique(user_id, article_id)",
        "This article is already bookmarked by that user.",
    )
