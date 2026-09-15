from odoo.tests import TransactionCase


class PayrollComponentsCommon(TransactionCase):
    """Shared fixtures: the shipped rate records and a helper to make staff."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.pf_config = cls.env.ref("drkds_in_payroll_components.pf_config_2026")
        cls.esi_config = cls.env.ref("drkds_in_payroll_components.esi_config_2026")
        cls.Slab = cls.env["drkds.in.pt.slab"]
        cls.maharashtra = cls.env.ref("base.state_in_mh")
        cls.west_bengal = cls.env.ref("base.state_in_wb")
        cls.karnataka = cls.env.ref("base.state_in_ka")

    @classmethod
    def _employee(cls, name, wage, **values):
        return cls.env["hr.employee"].create(dict({
            "name": name,
            "wage": wage,
            "company_id": cls.company.id,
        }, **values))
