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

    Base decides who may read an attachment from the record it belongs to,
    so a borrowed file keeps the access of its record. A reader who can see
    the document but not that record sees the document without its file
    (``preview_kind`` is ``restricted``); nothing here widens access to it.
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
        [("image", "Image"), ("pdf", "PDF"), ("other", "Other"), ("none", "No file"),
         ("restricted", "Not accessible")],
        compute="_compute_preview_kind",
        help="Which inline preview the form and the Kanban card use. Not accessible: "
        "the file belongs to a record you cannot open.",
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
    @api.depends_context("uid")
    def _compute_file(self):
        # Only a file the reader may open is read; the others read as empty
        # instead of failing the whole form or list for one borrowed file.
        readable = self.attachment_id._filtered_access("read")
        for document in self:
            attachment = document.attachment_id & readable
            document.file = attachment.datas
            document.file_name = attachment.name

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
    @api.depends_context("uid")
    def _compute_preview_kind(self):
        readable = self.attachment_id._filtered_access("read")
        for document in self:
            if not document.attachment_id:
                document.preview_kind = "none"
                continue
            if document.attachment_id not in readable:
                document.preview_kind = "restricted"
                continue
            mimetype = document.attachment_id.mimetype or ""
            if mimetype.startswith("image/"):
                document.preview_kind = "image"
            elif mimetype == "application/pdf":
                document.preview_kind = "pdf"
            else:
                document.preview_kind = "other"

    # -- access ------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            self._check_attachment_readable([vals.get("attachment_id") for vals in vals_list])
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.su and vals.get("attachment_id"):
            self._check_attachment_readable([vals["attachment_id"]])
        result = super().write(vals)
        if not self.env.su and ("folder_id" in vals or "company_id" in vals):
            # Record rules are checked against the values before the write.
            # Check the destination too: moving a document into a folder (or
            # a company) its mover may not file in is a write there.
            self.check_access("write")
        return result

    @api.model
    def _check_attachment_readable(self, attachment_ids):
        """A document may only point at a file its author can read; otherwise
        it would show the name, type and size of someone else's file."""
        attachments = self.env["ir.attachment"].browse([att_id for att_id in attachment_ids if att_id])
        attachments.check_access("read")

    def _readable_by(self, user):
        """The documents of ``self`` that ``user`` may read."""
        return self.with_user(user)._filtered_access("read").with_env(self.env)

    def _message_auto_subscribe_followers(self, updated_values, default_subtype_ids):
        # Mail subscribes the owner, and a follower receives every message
        # posted here. An owner who cannot read the document (outside the
        # folder's groups, or without document rights, as the poster of a
        # mirrored file may be) is left out.
        followers = super()._message_auto_subscribe_followers(updated_values, default_subtype_ids)
        owner = self.env["res.users"].sudo().browse(updated_values.get("user_id") or [])
        if owner and followers and self._readable_by(owner) != self:
            followers = [entry for entry in followers if entry[0] != owner.partner_id.id]
        return followers

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

        "Today" is the owner's date, in the owner's timezone: the job runs as
        OdooBot, with no timezone, whose date is UTC.

        Only an active owner who can open the document is reminded. A to-do
        for OdooBot is read by nobody, and an activity subscribes and notifies
        its assignee, which must not reach someone outside the folder. Such a
        document is not marked as reminded, so it is reminded once it has an
        owner who can open it; meanwhile it is listed under Expiring.
        """
        # No timezone is more than a day ahead of UTC.
        horizon = fields.Date.today() + timedelta(days=EXPIRY_WARNING_DAYS + 1)
        candidates = self.search([
            ("expiry_date", "!=", False),
            ("expiry_date", "<=", horizon),
        ]).filtered(lambda d: d.expiry_reminded_date != d.expiry_date)
        due = self.browse()
        for document in candidates:
            owner = document.user_id
            if not owner.active or not document._readable_by(owner):
                continue
            owner_today = fields.Date.context_today(document.with_context(tz=owner.tz or "UTC"))
            if document.expiry_date > owner_today + timedelta(days=EXPIRY_WARNING_DAYS):
                continue
            due |= document
            document.activity_schedule(
                "mail.mail_activity_data_todo",
                date_deadline=document.expiry_date,
                user_id=owner.id,
                summary=_("Document expires on %s", fields.Date.to_string(document.expiry_date)),
                note=_("The document %s in folder %s expires on %s.",
                       document.name, document.folder_id.complete_name,
                       fields.Date.to_string(document.expiry_date)),
            )
            document.expiry_reminded_date = document.expiry_date
        return due

    # -- mirroring ---------------------------------------------------------
    @api.model
    def _values_from_record(self, record, folder, default_company):
        """Company and contact of a document filed from ``record`` into
        ``folder``, consistent with each other so the company check passes.

        The company is the record's when the folder may hold it, else the
        folder's, else ``default_company``. The contact is the record itself
        for a contact, else the record's ``partner_id``, and is left out when
        it belongs to another company than the document.

        Returns ``(values, fits)``; ``fits`` is False when the record belongs
        to a company the folder is not kept for.
        """
        Company = self.env["res.company"]
        record_company = Company
        field = record._fields.get("company_id")
        if field is not None and field.comodel_name == "res.company":
            record_company = record.company_id
        fits = not (record_company and folder.company_id) or bool(
            folder.filtered_domain(folder._check_company_domain(record_company))
        )
        company = (record_company if fits else Company) or folder.company_id or default_company
        partner = self.env["res.partner"]
        if record._name == "res.partner":
            partner = record
        elif "partner_id" in record._fields and record._fields["partner_id"].comodel_name == "res.partner":
            partner = record.partner_id
        # Compared in sudo: the poster may not be allowed to read the contact.
        if partner and not partner.sudo().filtered_domain(partner._check_company_domain(company)):
            partner = self.env["res.partner"]
        return {"company_id": company.id, "partner_id": partner.id}, fits

    @api.model
    def _mirror_attachments(self, record, attachments, folder):
        """File ``attachments`` of ``record`` into ``folder`` as documents.

        Attachments already filed, and attachments that do not belong to the
        record, are skipped, and so is a record of a company the folder is not
        kept for. This runs inside someone's message post, so it must never
        fail it.

        Runs with elevated rights because the person who posted the file need
        not have any document access at all. That person is the owner, but
        follows the document only when they can read it (see
        ``_message_auto_subscribe_followers``).
        """
        attachments = attachments.sudo().filtered(
            lambda a: a.res_model == record._name and a.res_id == record.id
        )
        if not attachments:
            return self.browse()
        link_values, fits = self._values_from_record(record, folder, self.env["res.company"])
        if not fits:
            return self.browse()
        existing = self.sudo().search([("attachment_id", "in", attachments.ids)])
        done = set(existing.mapped("attachment_id").ids)
        owner = self.env.user if self.env.user._is_internal() else self.env["res.users"]
        vals_list = [{
            "name": attachment.name,
            "folder_id": folder.id,
            "attachment_id": attachment.id,
            "res_model": record._name,
            "res_id": record.id,
            "user_id": owner.id,
            **link_values,
        } for attachment in attachments if attachment.id not in done]
        return self.sudo().with_context(mail_create_nosubscribe=True).create(vals_list)
