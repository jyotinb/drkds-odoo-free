from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    drkds_hr_document_responsible_id = fields.Many2one(
        "res.users", string="Document Reminder Fallback",
        domain="[('share', '=', False)]",
        help="Receives the document expiry reminders of employees who have "
        "no HR responsible of their own.",
    )
