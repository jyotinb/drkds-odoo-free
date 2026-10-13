import base64
from datetime import date

from odoo.tests import TransactionCase, new_test_user

TODAY = date(2026, 10, 13)


class DocumentExpiryCommon(TransactionCase):
    """Three employees, two HR users, three document types.

    Passport: expiry required, reminder 90 days before, mandatory.
    Contract: expiry required, reminder 30 days before, mandatory.
    Certificate: no expiry, not mandatory.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.Document = cls.env["drkds.hr.document"]
        cls.DocType = cls.env["drkds.hr.document.type"]
        cls.Employee = cls.env["hr.employee"]
        cls.activity_type = cls.env.ref(
            "drkds_hr_document_expiry_lite.mail_activity_data_document_expiry"
        )

        cls.hr_officer = new_test_user(
            cls.env, login="drkds_hdl_officer", name="HR Officer",
            groups="base.group_user,hr.group_hr_user",
        )
        cls.hr_manager = new_test_user(
            cls.env, login="drkds_hdl_manager", name="HR Manager",
            groups="base.group_user,hr.group_hr_manager",
        )
        cls.fallback_user = new_test_user(
            cls.env, login="drkds_hdl_fallback", name="Fallback HR",
            groups="base.group_user,hr.group_hr_user",
        )
        cls.plain_user = new_test_user(
            cls.env, login="drkds_hdl_plain", name="Plain Employee",
            groups="base.group_user",
        )

        # The shipped types are left alone; the tests use their own so that
        # a site that edits the shipped ones does not change the figures.
        cls.type_passport = cls.DocType.create({
            "name": "Test Passport", "requires_expiry": True,
            "remind_days": 90, "mandatory": True,
        })
        cls.type_contract = cls.DocType.create({
            "name": "Test Contract", "requires_expiry": True,
            "remind_days": 30, "mandatory": True,
        })
        cls.type_certificate = cls.DocType.create({
            "name": "Test Certificate", "requires_expiry": False,
            "remind_days": 0, "mandatory": False,
        })

        cls.emp_asha = cls._employee("Asha Nair", hr_responsible_id=cls.hr_officer.id)
        cls.emp_ravi = cls._employee("Ravi Menon", hr_responsible_id=cls.hr_manager.id)
        cls.emp_priya = cls._employee("Priya Shah", hr_responsible_id=cls.hr_officer.id)

    @classmethod
    def _employee(cls, name, **values):
        # The status is dated in the employee's timezone. Pin it, so that the
        # figures do not depend on the timezone of the database's admin or
        # working-hours calendar, which new employees inherit.
        return cls.Employee.create(dict({
            "name": name,
            "company_id": cls.company.id,
            "tz": "Asia/Kolkata",
        }, **values))

    @classmethod
    def _file(cls, text):
        return base64.b64encode(text.encode())

    def _document(self, employee, doc_type, expiry=None, **values):
        vals = {
            "employee_id": employee.id,
            "type_id": doc_type.id,
            "expiry_date": expiry,
            "file": self._file(f"scan of {doc_type.name}"),
            "file_name": "scan.pdf",
        }
        vals.update(values)
        return self.Document.create(vals)

    def _reminders(self, document=None):
        domain = [
            ("res_model", "=", "drkds.hr.document"),
            ("activity_type_id", "=", self.activity_type.id),
        ]
        if document is not None:
            domain.append(("res_id", "=", document.id))
        return self.env["mail.activity"].search(domain)
