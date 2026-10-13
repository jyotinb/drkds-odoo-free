from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DrkdsDocumentFolder(models.Model):
    """A shelf in the document store.

    Folders nest freely; ``_parent_store`` keeps a materialised path so
    "everything under this folder" is one indexed ``child_of`` query.

    Access is decided per folder by two group lists. A folder with no read
    group is open to every document user. A folder with read groups is
    invisible, documents included, to a user outside them. The write groups
    say who may add, change and delete documents in it; left empty, anyone who
    can read the folder can write in it. The record rules in
    ``security/drkds_documents_rules.xml`` turn these lists into domains.
    """

    _name = "drkds.document.folder"
    _description = "Document Folder"
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = "complete_name"
    _order = "complete_name"
    _check_company_auto = True

    name = fields.Char(required=True, translate=True, index="trigram")
    complete_name = fields.Char(
        string="Full Path", compute="_compute_complete_name", recursive=True, store=True,
        help="The folder name prefixed by every ancestor, for example Legal / Contracts / 2026.",
    )
    parent_id = fields.Many2one(
        "drkds.document.folder", string="Parent Folder", index=True, ondelete="restrict",
        check_company=True,
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many("drkds.document.folder", "parent_id", string="Sub-folders")
    sequence = fields.Integer(default=10, help="Order of the folder among its siblings.")
    company_id = fields.Many2one(
        "res.company", string="Company", index=True,
        help="Leave empty for a folder shared by every company.",
    )
    read_group_ids = fields.Many2many(
        "res.groups", "drkds_document_folder_read_group_rel", "folder_id", "group_id",
        string="Read Groups",
        help="Only members of these groups see the folder and its documents. "
        "Empty: every document user sees it.",
    )
    write_group_ids = fields.Many2many(
        "res.groups", "drkds_document_folder_write_group_rel", "folder_id", "group_id",
        string="Write Groups",
        help="Only members of these groups may add, change or delete documents here. "
        "Empty: anyone who can see the folder.",
    )
    model_id = fields.Many2one(
        "ir.model", string="Mirrored Model", ondelete="set null", index=True,
        domain="[('is_mail_thread', '=', True), ('transient', '=', False)]",
        help="Files posted in the chatter of records of this model are filed here "
        "automatically. Set from Settings > Document Folders.",
    )
    description = fields.Char(translate=True, help="One line saying what belongs here.")
    document_ids = fields.One2many("drkds.document", "folder_id", string="Filed Documents")
    document_count = fields.Integer(compute="_compute_document_count", string="Documents")
    document_count_total = fields.Integer(
        compute="_compute_document_count", string="Documents (with sub-folders)",
    )
    active = fields.Boolean(default=True)

    _model_uniq = models.Constraint(
        "unique(model_id)", "Only one folder can mirror a given model.",
    )

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for folder in self:
            if folder.parent_id:
                folder.complete_name = f"{folder.parent_id.complete_name} / {folder.name}"
            else:
                folder.complete_name = folder.name

    def _compute_document_count(self):
        Document = self.env["drkds.document"]
        direct = dict(Document._read_group(
            [("folder_id", "in", self.ids)], ["folder_id"], ["__count"],
        ))
        branch = dict(Document._read_group(
            [("folder_id", "child_of", self.ids)], ["folder_id"], ["__count"],
        ))
        for folder in self:
            folder.document_count = direct.get(folder, 0)
            descendants = self.search([("id", "child_of", folder.id)])
            folder.document_count_total = sum(branch.get(node, 0) for node in descendants)

    @api.constrains("parent_id")
    def _check_folder_recursion(self):
        if self._has_cycle():
            raise ValidationError(_("A folder cannot be placed inside one of its own sub-folders."))

    @api.model_create_multi
    def create(self, vals_list):
        # A new sub-folder starts with its parent's access lists, so a
        # restricted branch does not sprout an open leaf by accident. The
        # manager can still change them afterwards.
        for vals in vals_list:
            parent = self.browse(vals.get("parent_id")) if vals.get("parent_id") else None
            if parent:
                if "read_group_ids" not in vals and parent.read_group_ids:
                    vals["read_group_ids"] = [(6, 0, parent.read_group_ids.ids)]
                if "write_group_ids" not in vals and parent.write_group_ids:
                    vals["write_group_ids"] = [(6, 0, parent.write_group_ids.ids)]
                if "company_id" not in vals and parent.company_id:
                    vals["company_id"] = parent.company_id.id
        return super().create(vals_list)

    @api.model
    def _get_mirror_folder(self, model_name):
        """The folder that mirrors ``model_name``, or an empty recordset.

        Looked up with elevated rights: the hook that calls this runs for
        whoever posted the message, who may well not see the folder.
        """
        return self.sudo().search([("model_id.model", "=", model_name)], limit=1)

    def action_open_documents(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "drkds_documents_lite.action_drkds_document"
        )
        action["domain"] = [("folder_id", "child_of", self.id)]
        action["context"] = {"default_folder_id": self.id, "search_default_group_folder": 1}
        return action
