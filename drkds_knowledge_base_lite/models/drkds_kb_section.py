from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DrkdsKbSection(models.Model):
    """A shelf in the knowledge base.

    Sections nest freely. ``_parent_store`` keeps a materialised
    ``parent_path`` on every row, so ``child_of`` domains - which is how the
    sidebar tree and the "articles in this branch" counters are built - resolve
    in a single indexed query instead of walking the tree in Python.
    """

    _name = "drkds.lite.kb.section"
    _description = "Knowledge Base Section"
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = "complete_name"
    _order = "complete_name"

    name = fields.Char(required=True, translate=True, index="trigram")
    complete_name = fields.Char(
        string="Full Path",
        compute="_compute_complete_name",
        recursive=True,
        store=True,
        help="The section name prefixed by every ancestor, for example "
        "Handbook / Onboarding / First Week.",
    )
    parent_id = fields.Many2one(
        "drkds.lite.kb.section", string="Parent Section", index=True, ondelete="restrict",
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many("drkds.lite.kb.section", "parent_id", string="Sub-sections")
    sequence = fields.Integer(default=10, help="Order of the section among its siblings.")
    description = fields.Char(
        translate=True, help="One line telling a reader what belongs in this section.",
    )
    article_ids = fields.One2many("drkds.lite.kb.article", "section_id", string="Articles")
    article_count = fields.Integer(
        string="Article Count", compute="_compute_article_count",
        help="Articles filed directly in this section.",
    )
    article_count_total = fields.Integer(
        string="Articles (with sub-sections)", compute="_compute_article_count",
    )
    active = fields.Boolean(default=True)

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for section in self:
            if section.parent_id:
                section.complete_name = f"{section.parent_id.complete_name} / {section.name}"
            else:
                section.complete_name = section.name

    def _compute_article_count(self):
        Article = self.env["drkds.lite.kb.article"]
        direct = dict(Article._read_group(
            [("section_id", "in", self.ids)], ["section_id"], ["__count"],
        ))
        branch = dict(Article._read_group(
            [("section_id", "child_of", self.ids)], ["section_id"], ["__count"],
        ))
        for section in self:
            section.article_count = direct.get(section, 0)
            descendants = self.search([("id", "child_of", section.id)])
            section.article_count_total = sum(branch.get(node, 0) for node in descendants)

    @api.constrains("parent_id")
    def _check_section_recursion(self):
        if self._has_cycle():
            raise ValidationError(
                _("A section cannot be placed inside one of its own sub-sections.")
            )

    def action_open_articles(self):
        """Open the reading list restricted to this branch of the tree."""
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "drkds_knowledge_base_lite.action_drkds_kb_article"
        )
        action["domain"] = [("section_id", "child_of", self.id)]
        action["context"] = {"default_section_id": self.id}
        return action
