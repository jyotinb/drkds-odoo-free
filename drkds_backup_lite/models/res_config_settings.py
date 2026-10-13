from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    drkds_backup_default_folder = fields.Char(
        string="Default Backup Folder",
        config_parameter="drkds_backup_lite.default_folder",
        help="Proposed as the folder of every new backup configuration.",
    )

    def action_drkds_open_backup_configs(self):
        return self.env["ir.actions.actions"]._for_xml_id(
            "drkds_backup_lite.action_drkds_backup_config"
        )
