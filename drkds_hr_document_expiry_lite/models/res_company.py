from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    drkds_hr_document_responsible_id = fields.Many2one(
        "res.users", string="Document Reminder Fallback",
        # The reminder job only assigns an HR officer of the document's
        # company; offer nobody else. Callable, so that the related settings
        # field inherits it (a string domain would not carry over).
        domain=lambda self: [
            ("share", "=", False),
            ("company_ids", "in", self.env.company.ids),
            ("all_group_ids", "in", self.env.ref("hr.group_hr_user").ids),
        ],
        help="An HR officer of this company who receives the document expiry "
        "reminders of employees whose own HR responsible cannot take them.",
    )
