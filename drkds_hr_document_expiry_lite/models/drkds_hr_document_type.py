from odoo import api, fields, models


class DrkdsHrDocumentType(models.Model):
    """A kind of employee document: passport, contract, work permit.

    The type carries the rules that every document of that kind follows:
    whether it has an expiry date at all, how many days before the expiry
    HR should be told, and whether every employee is expected to hold one.
    """

    _name = "drkds.hr.document.type"
    _description = "Employee Document Type"
    _order = "sequence, name, id"
    _check_company_auto = True

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    requires_expiry = fields.Boolean(
        string="Has Expiry Date", default=True,
        help="A document of this type must carry an expiry date. Untick for "
        "documents that never lapse, such as a degree certificate.",
    )
    remind_days = fields.Integer(
        string="Remind Days Before", default=30,
        help="A document moves to Expiring this many days before its expiry "
        "date, and the HR responsible gets an activity.",
    )
    mandatory = fields.Boolean(
        string="Mandatory for Every Employee",
        help="Employees without an active document of this type show up under "
        "the Missing Mandatory Documents filter.",
    )
    description = fields.Text(translate=True)
    company_id = fields.Many2one(
        "res.company", string="Company", index=True,
        help="Leave empty to share the type across companies.",
    )
    document_count = fields.Integer(compute="_compute_document_count")

    _remind_days_positive = models.Constraint(
        "CHECK(remind_days >= 0)",
        "The reminder window cannot be negative.",
    )

    def _compute_document_count(self):
        groups = self.env["drkds.hr.document"]._read_group(
            [("type_id", "in", self.ids)], ["type_id"], ["__count"]
        )
        counts = {doc_type.id: count for doc_type, count in groups}
        for doc_type in self:
            doc_type.document_count = counts.get(doc_type.id, 0)

    def action_view_documents(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "drkds_hr_document_expiry_lite.action_drkds_hr_document"
        )
        action["domain"] = [("type_id", "=", self.id)]
        action["context"] = {"default_type_id": self.id}
        return action

    @api.model
    def _mandatory_types_for_company(self, company):
        """Mandatory, active types that apply to ``company``: the ones bound to
        it and the ones shared across companies."""
        return self.search([
            ("mandatory", "=", True),
            "|", ("company_id", "=", False), ("company_id", "=", company.id),
        ])
