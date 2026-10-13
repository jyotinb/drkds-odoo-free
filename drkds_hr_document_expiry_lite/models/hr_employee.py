from odoo import api, fields, models


class HrEmployee(models.Model):
    """The documents tab, the smart button and the missing-mandatory check."""

    _inherit = "hr.employee"

    drkds_hr_document_ids = fields.One2many(
        "drkds.hr.document", "employee_id", string="Documents",
        groups="hr.group_hr_user",
    )
    drkds_hr_document_count = fields.Integer(
        compute="_compute_drkds_hr_document_counts", groups="hr.group_hr_user",
    )
    drkds_hr_expired_document_count = fields.Integer(
        compute="_compute_drkds_hr_document_counts", groups="hr.group_hr_user",
    )
    drkds_hr_missing_mandatory = fields.Boolean(
        string="Missing Mandatory Documents",
        compute="_compute_drkds_hr_missing_mandatory",
        search="_search_drkds_hr_missing_mandatory",
        groups="hr.group_hr_user",
    )
    drkds_hr_missing_type_ids = fields.Many2many(
        "drkds.hr.document.type", string="Missing Document Types",
        compute="_compute_drkds_hr_missing_mandatory", groups="hr.group_hr_user",
    )

    def unlink(self):
        """Delete the employees' documents through the ORM first.

        ``employee_id`` cascades in SQL, which drops the document rows but not
        what refers to them by model and id: the scanned file, the open
        reminder, the chatter and the followers would outlive the employee,
        the passport scan included. Done in sudo, after the caller's own
        access check, because deleting the employee deletes the documents
        anyway; archived documents go too.
        """
        self.check_access("unlink")
        self.env["drkds.hr.document"].sudo().search([
            ("employee_id", "in", self.ids), ("active", "in", [True, False]),
        ]).unlink()
        return super().unlink()

    @api.depends("drkds_hr_document_ids.state", "drkds_hr_document_ids.active")
    def _compute_drkds_hr_document_counts(self):
        groups = self.env["drkds.hr.document"]._read_group(
            [("employee_id", "in", self.ids)], ["employee_id", "state"], ["__count"],
        )
        totals, expired = {}, {}
        for employee, state, count in groups:
            totals[employee.id] = totals.get(employee.id, 0) + count
            if state == "expired":
                expired[employee.id] = expired.get(employee.id, 0) + count
        for employee in self:
            employee.drkds_hr_document_count = totals.get(employee.id, 0)
            employee.drkds_hr_expired_document_count = expired.get(employee.id, 0)

    @api.model
    def _drkds_hr_missing_map(self, employees):
        """{employee: types it lacks} for the mandatory types of its company."""
        DocType = self.env["drkds.hr.document.type"]
        held = {}
        for employee, doc_type in self.env["drkds.hr.document"]._read_group(
            [("employee_id", "in", employees.ids)], ["employee_id", "type_id"],
        ):
            held.setdefault(employee.id, set()).add(doc_type.id)
        by_company = {}
        result = {}
        for employee in employees:
            company = employee.company_id
            if company.id not in by_company:
                by_company[company.id] = DocType._mandatory_types_for_company(company)
            missing = by_company[company.id].filtered(
                lambda t: t.id not in held.get(employee.id, set())
            )
            result[employee] = missing
        return result

    @api.depends("drkds_hr_document_ids.type_id", "drkds_hr_document_ids.active", "company_id")
    def _compute_drkds_hr_missing_mandatory(self):
        missing_map = self._drkds_hr_missing_map(self)
        for employee in self:
            missing = missing_map.get(employee, self.env["drkds.hr.document.type"])
            employee.drkds_hr_missing_type_ids = missing
            employee.drkds_hr_missing_mandatory = bool(missing)

    def _search_drkds_hr_missing_mandatory(self, operator, value):
        """Handles =, != and the in / not in forms the ORM passes for booleans."""
        if operator in ("in", "not in"):
            # Odoo 19 hands an OrderedSet here, so test for iterability.
            values = {value} if isinstance(value, (bool, int, str)) else set(value)
            if len(values) != 1:
                return [] if operator == "in" else [("id", "=", False)]
            value = next(iter(values))
            operator = "=" if operator == "in" else "!="
        if operator not in ("=", "!="):
            raise NotImplementedError(f"Unsupported operator {operator}")
        want_missing = (operator == "=") == bool(value)
        employees = self.search([("active", "in", [True, False])])
        missing_ids = [
            employee.id for employee, missing in self._drkds_hr_missing_map(employees).items()
            if missing
        ]
        return [("id", "in" if want_missing else "not in", missing_ids)]

    def action_view_drkds_hr_documents(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "drkds_hr_document_expiry_lite.action_drkds_hr_document"
        )
        action["domain"] = [("employee_id", "=", self.id)]
        action["context"] = {
            "default_employee_id": self.id,
            "search_default_employee_id": self.id,
        }
        return action
