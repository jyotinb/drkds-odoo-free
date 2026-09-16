from odoo import models


class IrActionsReport(models.Model):
    """Let a label template decide the paper size of the label report.

    A report action carries a single paper format, but this module has one paper
    format per label template. The print wizard puts the chosen template in the
    context, and the report action honours it here. Every other report is left
    exactly as it was.
    """

    _inherit = "ir.actions.report"

    def get_paperformat(self):
        template_id = self.env.context.get("drkds_label_template_id")
        if template_id and self.report_name == "drkds_label_designer_lite.report_drkds_label":
            template = self.env["drkds.lite.label.template"].sudo().browse(template_id).exists()
            if template.paperformat_id:
                return template.paperformat_id
        return super().get_paperformat()
