from datetime import timedelta

from odoo import _, api, fields, models
from odoo.fields import Domain
from odoo.exceptions import UserError

EXPIRY_WARNING_DAYS = 7


class DrkdsDocument(models.Model):
    """One filed file.

    The bytes live in an ``ir.attachment``. A document uploaded through the
    form owns its attachment (``res_model`` is this model). A document made
    by "Add to Documents" or by chatter mirroring only points at an
    attachment that belongs to another record; the file is not copied and
    deleting the document never deletes it.
    """

    _name = "drkds.document"
    _description = "Document"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(required=True, index="trigram", tracking=True)
    folder_id = fields.Many2one(
        "drkds.document.folder", string="Folder", required=True, index=True,
        ondelete="restrict", check_company=True, tracking=True,
    )
    company_id = fields.Many2one(
        "res.company", string="Company", index=True, default=lambda self: self.env.company,
    )
    attachment_id = fields.Many2one(
        "ir.attachment", string="Attachment", ondelete="set null", copy=False, index=True,
        help="The stored file. Deleting the document never deletes the file of a "
        "record it was taken from.",
    )
    file = fields.Binary(
        string="File", compute="_compute_file", inverse="_inverse_file", attachment=False,
    )
    file_name = fields.Char(
        string="File Name", compute="_compute_file", inverse="_inverse_file",
    )
    mimetype = fields.Char(string="Type", related="attachment_id.mimetype")
    file_size = fields.Integer(string="Size", related="attachment_id.file_size")
    preview_kind = fields.Selection(
        [("image", "Image"), ("pdf", "PDF"), ("other", "Other"), ("none", "No file")],
        compute="_compute_preview_kind",
        help="Which inline preview the form and the Kanban card use.",
    )
    tag_ids = fields.Many2many(
        "drkds.document.tag", "drkds_document_tag_rel", "document_id", "tag_id", string="Tags",
    )
    user_id = fields.Many2one(
        "res.users", string="Owner", default=lambda self: self.env.user, index=True,
        tracking=True, domain=[("share", "=", False)],
    )
    partner_id = fields.Many2one(
        "res.partner", string="Contact", index=True, tracking=True, check_company=True,
    )
    res_model = fields.Char(string="Linked Model", index=True, copy=False)
    res_id = fields.Many2oneReference(
        string="Linked Record ID", model_field="res_model", index=True, copy=False,
    )
    res_name = fields.Char(string="Linked Record", compute="_compute_res_name")
    description = fields.Text()
    expiry_date = fields.Date(tracking=True, index=True)
    expiry_reminded_date = fields.Date(
        copy=False,
        help="The expiry date a reminder was last scheduled for. Changing the expiry "
        "date makes the reminder job fire again.",
    )
    expiry_state = fields.Selection(
        [("none", "No expiry"), ("ok", "Valid"), ("soon", "Expires soon"), ("expired", "Expired")],
        compute="_compute_expiry_state", search="_search_expiry_state",
    )
    active = fields.Boolean(default=True)
    color = fields.Integer()

    # -- file ------------------------------------------------------------
    @api.depends("attachment_id", "attachment_id.datas", "attachment_id.name")
    def _compute_file(self):
        for document in self:
            document.file = document.attachment_id.datas
            document.file_name = document.attachment_id.name

    def _owns_attachment(self):
        self.ensure_one()
        attachment = self.attachment_id
        return bool(
            attachment and attachment.res_model == self._name and attachment.res_id == self.id
        )

    def _inverse_file(self):
        Attachment = self.env["ir.attachment"]
        for document in self:
            data = document.file
            name = document.file_name or document.name
            if not data:
                # The file was cleared. A file we own goes; a borrowed one
                # is merely unlinked and stays with its record.
                if document._owns_attachment():
                    document.attachment_id.unlink()
                document.attachment_id = False
                continue
            if document._owns_attachment():
                document.attachment_id.write({"datas": data, "name": name})
            else:
                document.attachment_id = Attachment.create({
                    "name": name,
                    "datas": data,
                    "res_model": self._name,
                    "res_id": document.id,
                })

    @api.depends("attachment_id.mimetype")
    def _compute_preview_kind(self):
        for document in self:
            mimetype = document.attachment_id.mimetype or ""
            if not document.attachment_id:
                document.preview_kind = "none"
            elif mimetype.startswith("image/"):
                document.preview_kind = "image"
            elif mimetype == "application/pdf":
                document.preview_kind = "pdf"
            else:
                document.preview_kind = "other"

    # -- linked record ---------------------------------------------------
    @api.depends("res_model", "res_id")
    def _compute_res_name(self):
        for document in self:
            name = False
            model = document.res_model
            if model and document.res_id and model in self.env:
                record = self.env[model].browse(document.res_id)
                if record.exists() and record.has_access("read"):
                    name = record.display_name
            document.res_name = name

    def action_open_linked_record(self):
        self.ensure_one()
        if not (self.res_model and self.res_id and self.res_model in self.env):
            raise UserError(_("This document is not linked to a record."))
        return {
            "type": "ir.actions.act_window",
            "res_model": self.res_model,
            "res_id": self.res_id,
            "view_mode": "form",
            "target": "current",
        }

    def action_download(self):
        self.ensure_one()
        if not self.attachment_id:
            raise UserError(_("This document has no file."))
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{self.attachment_id.id}?download=true",
            "target": "self",
        }

    # -- expiry ----------------------------------------------------------
    @api.depends("expiry_date")
    @api.depends_context("today")
    def _compute_expiry_state(self):
        today = fields.Date.context_today(self)
        soon = today + timedelta(days=EXPIRY_WARNING_DAYS)
        for document in self:
            date = document.expiry_date
            if not date:
                document.expiry_state = "none"
            elif date < today:
                document.expiry_state = "expired"
            elif date <= soon:
                document.expiry_state = "soon"
            else:
                document.expiry_state = "ok"

    def _search_expiry_state(self, operator, value):
        today = fields.Date.context_today(self)
        soon = today + timedelta(days=EXPIRY_WARNING_DAYS)
        domains = {
            "none": [("expiry_date", "=", False)],
            "expired": [("expiry_date", "<", today)],
            "soon": [("expiry_date", ">=", today), ("expiry_date", "<=", soon)],
            "ok": [("expiry_date", ">", soon)],
        }
        if operator in ("=", "in"):
            values = [value] if isinstance(value, str) else list(value)
            positive = True
        elif operator in ("!=", "not in"):
            values = [value] if isinstance(value, str) else list(value)
            positive = False
        else:
            raise UserError(_("Unsupported search on expiry state."))
        wanted = [v for v in values if v in domains]
        if not positive:
            wanted = [v for v in domains if v not in wanted]
        if not wanted:
            return Domain.FALSE
        return Domain.OR(Domain(domains[state]) for state in wanted)

    @api.model
    def _cron_drkds_expiry_reminder(self):
        """Schedule a to-do for the owner of every document that expires
        within ``EXPIRY_WARNING_DAYS`` and has not been reminded for that date.

        Idempotent: ``expiry_reminded_date`` records the date reminded for, so
        a second run on the same day does nothing and a moved expiry date is
        reminded again.
        """
        today = fields.Date.today()
        limit = today + timedelta(days=EXPIRY_WARNING_DAYS)
        candidates = self.search([
            ("expiry_date", "!=", False),
            ("expiry_date", "<=", limit),
        ])
        due = candidates.filtered(lambda d: d.expiry_reminded_date != d.expiry_date)
        for document in due:
            user = document.user_id if document.user_id and document.user_id.active else self.env.user
            document.activity_schedule(
                "mail.mail_activity_data_todo",
                date_deadline=document.expiry_date,
                user_id=user.id,
                summary=_("Document expires on %s", fields.Date.to_string(document.expiry_date)),
                note=_("The document %s in folder %s expires on %s.",
                       document.name, document.folder_id.complete_name,
                       fields.Date.to_string(document.expiry_date)),
            )
            document.expiry_reminded_date = document.expiry_date
        return due

    # -- mirroring ---------------------------------------------------------
    @api.model
    def _mirror_attachments(self, record, attachments, folder):
        """File ``attachments`` of ``record`` into ``folder`` as documents.

        Attachments already filed, and attachments that do not belong to the
        record, are skipped. Runs with elevated rights because the person who
        posted the file need not have any document access at all.
        """
        attachments = attachments.sudo().filtered(
            lambda a: a.res_model == record._name and a.res_id == record.id
        )
        if not attachments:
            return self.browse()
        existing = self.sudo().search([("attachment_id", "in", attachments.ids)])
        done = set(existing.mapped("attachment_id").ids)
        owner = self.env.user if self.env.user._is_internal() else self.env["res.users"]
        partner = self.env["res.partner"]
        if record._name == "res.partner":
            partner = record
        elif "partner_id" in record._fields and record._fields["partner_id"].comodel_name == "res.partner":
            partner = record.partner_id
        company = self.env["res.company"]
        if "company_id" in record._fields and record._fields["company_id"].comodel_name == "res.company":
            company = record.company_id
        if folder.company_id and (not company or company != folder.company_id):
            company = folder.company_id
        vals_list = [{
            "name": attachment.name,
            "folder_id": folder.id,
            "attachment_id": attachment.id,
            "res_model": record._name,
            "res_id": record.id,
            "user_id": owner.id,
            "partner_id": partner.id,
            "company_id": company.id,
        } for attachment in attachments if attachment.id not in done]
        return self.sudo().create(vals_list)
