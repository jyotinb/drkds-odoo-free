from odoo import _, api, fields, models
from odoo.tools import html2plaintext


class DrkdsKbArticle(models.Model):
    """One article: a title, a body, and enough metadata to find it again.

    The body is HTML, which is pleasant to read but useless to search - a
    reader looking for "reimbursement" should not have to know whether the word
    sits inside a ``<strong>``. So every save also stores a flattened plain-text
    copy in ``body_text``, and the search view searches that. The copy is a
    stored compute, never edited by hand, so it cannot drift from the body.
    """

    _name = "drkds.lite.kb.article"
    _description = "Knowledge Base Article"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "write_date desc, id desc"

    name = fields.Char(
        string="Title", required=True, translate=True, index="trigram", tracking=True,
    )
    body = fields.Html(
        string="Article", sanitize=True, sanitize_style=True,
        help="The article itself. Headings, lists, tables and images are kept.",
    )
    body_text = fields.Text(
        string="Body (plain text)",
        compute="_compute_body_text",
        store=True,
        readonly=True,
        help="Flattened copy of the body, kept so that a full text search can "
        "reach words that appear only inside the article.",
    )
    full_text = fields.Char(
        string="Search",
        store=False,
        search="_search_full_text",
        help="Virtual field: searching it looks in the title, the body and the tags.",
    )
    section_id = fields.Many2one(
        "drkds.lite.kb.section", string="Section", index=True, ondelete="restrict",
        tracking=True,
    )
    section_path = fields.Char(
        string="Filed Under", related="section_id.complete_name", store=True,
    )
    tag_ids = fields.Many2many(
        "drkds.lite.kb.tag", "drkds_lite_kb_article_tag_rel", "article_id", "tag_id",
        string="Tags",
    )
    author_id = fields.Many2one(
        "res.users", string="Author", index=True, tracking=True,
        default=lambda self: self.env.user, ondelete="restrict",
    )
    editor_id = fields.Many2one(
        "res.users", string="Last Edited By", readonly=True, ondelete="restrict",
        help="Whoever saved the article last. Set automatically.",
    )
    state = fields.Selection(
        [("draft", "Draft"), ("published", "Published")],
        string="Status", default="draft", required=True, tracking=True,
        help="A draft is visible only to editors. Publishing shows the article "
        "to every reader.",
    )
    published_date = fields.Datetime(string="Published On", readonly=True, copy=False)
    favourite_ids = fields.One2many(
        "drkds.kb.favourite", "article_id", string="Bookmarks",
    )
    is_favourite = fields.Boolean(
        string="Bookmarked",
        compute="_compute_is_favourite",
        search="_search_is_favourite",
        help="Your own bookmark on this article. Bookmarks are per user.",
    )
    favourite_count = fields.Integer(
        string="Bookmark Count", compute="_compute_favourite_count",
    )
    active = fields.Boolean(default=True)

    # -- computes ------------------------------------------------------
    @api.depends("body")
    def _compute_body_text(self):
        for article in self:
            article.body_text = html2plaintext(article.body) if article.body else False

    @api.depends_context("uid")
    def _compute_is_favourite(self):
        favoured = self.env["drkds.kb.favourite"].search([
            ("article_id", "in", self.ids), ("user_id", "=", self.env.uid),
        ]).article_id
        for article in self:
            article.is_favourite = article in favoured

    def _compute_favourite_count(self):
        counts = dict(self.env["drkds.kb.favourite"]._read_group(
            [("article_id", "in", self.ids)], ["article_id"], ["__count"],
        ))
        for article in self:
            article.favourite_count = counts.get(article, 0)

    # -- searches ------------------------------------------------------
    def _search_full_text(self, operator, value):
        """Search title, flattened body and tag names at once.

        Only the text operators are meaningful here; anything else would be a
        programming mistake and is reported as such rather than silently
        matching everything.
        """
        if operator not in ("like", "ilike", "not like", "not ilike", "=", "!="):
            raise NotImplementedError(
                _("The article search field only supports text comparisons.")
            )
        negative = operator in ("not like", "not ilike", "!=")
        positive = {"not like": "like", "not ilike": "ilike", "!=": "="}.get(
            operator, operator
        )
        domain = [
            "|", "|",
            ("name", positive, value),
            ("body_text", positive, value),
            ("tag_ids.name", positive, value),
        ]
        return ["!"] + domain if negative else domain

    def _search_is_favourite(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            raise NotImplementedError(_("Bookmarks can only be searched as a flag."))
        mine = self.env["drkds.kb.favourite"].search(
            [("user_id", "=", self.env.uid)]
        ).article_id.ids
        wanted = value if operator == "=" else not value
        return [("id", "in" if wanted else "not in", mine)]

    # -- orm -----------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault("editor_id", self.env.uid)
            if vals.get("state") == "published" and not vals.get("published_date"):
                vals["published_date"] = fields.Datetime.now()
        return super().create(vals_list)

    def write(self, vals):
        tracked = {"name", "body", "section_id", "tag_ids", "state"}
        if tracked & set(vals) and "editor_id" not in vals:
            vals["editor_id"] = self.env.uid
        if vals.get("state") == "published":
            vals.setdefault("published_date", fields.Datetime.now())
        return super().write(vals)

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if "name" not in default:
            for article, vals in zip(self, vals_list):
                vals["name"] = _("%s (copy)", article.name)
        return vals_list

    # -- actions -------------------------------------------------------
    def action_publish(self):
        self.write({"state": "published"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})

    def action_toggle_favourite(self):
        """Add or remove the current user's bookmark on each article."""
        Favourite = self.env["drkds.kb.favourite"]
        for article in self:
            existing = Favourite.search([
                ("article_id", "=", article.id), ("user_id", "=", self.env.uid),
            ], limit=1)
            if existing:
                existing.unlink()
            else:
                Favourite.create({"article_id": article.id, "user_id": self.env.uid})
        return True
