from odoo import api, fields, models


class HrVersion(models.Model):
    """Statutory Indian payroll identifiers and switches on the contract.

    In Odoo 19 the contract lives on ``hr.version``, and ``hr.employee``
    delegates to it, so every field added here is also readable and writable on
    the employee record. Aadhaar is deliberately absent: it is never stored by
    this module. UAN, PF and ESI numbers are employer-facing identifiers and
    are kept.
    """

    _inherit = "hr.version"

    drkds_in_pf_applicable = fields.Boolean(
        string="PF Applicable", default=False,
        help="Deduct and contribute Provident Fund for this contract.",
    )
    drkds_in_pf_on_actual_wage = fields.Boolean(
        string="PF on Actual Wage", default=False,
        help="Contribute PF on the full wage instead of capping it at the "
        "statutory wage ceiling. Contributions above the ceiling are voluntary.",
    )
    drkds_in_pf_number = fields.Char(
        string="PF Account Number",
        help="Establishment PF account number of the member.",
    )
    drkds_in_uan = fields.Char(
        string="UAN",
        help="Universal Account Number, twelve digits, issued by EPFO.",
    )

    drkds_in_esi_applicable = fields.Boolean(
        string="ESI Applicable", default=False,
        help="Deduct and contribute ESI for this contract, subject to the "
        "gross wage threshold.",
    )
    drkds_in_esi_number = fields.Char(
        string="ESI Number",
        help="Insurance number issued by ESIC, seventeen digits.",
    )
    drkds_in_esi_covered_since = fields.Date(
        string="ESI Covered Since",
        help="Date on which the employee last became covered by ESI. When the "
        "wage later crosses the threshold inside the same contribution period, "
        "coverage continues until that period ends.",
    )

    drkds_in_pt_applicable = fields.Boolean(
        string="Professional Tax Applicable", default=False,
        help="Deduct professional tax for this contract.",
    )
    drkds_in_pt_state_id = fields.Many2one(
        "res.country.state", string="Professional Tax State",
        domain="[('country_id.code', '=', 'IN')]",
        help="State whose professional tax schedule applies. Professional tax "
        "is a state levy, so this is usually the state of the work location "
        "rather than the state of residence.",
    )

    @api.onchange("drkds_in_uan")
    def _onchange_drkds_in_uan(self):
        for version in self:
            if version.drkds_in_uan:
                version.drkds_in_uan = "".join(version.drkds_in_uan.split())

