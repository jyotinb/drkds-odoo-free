# Part of the drkds free suite for Odoo 19 Community. See LICENSE (LGPL-3).
"""One setting: how many days of login history the purge keeps."""

from odoo import fields, models

from .drkds_login_record import PURGE_DAYS_DEFAULT, PURGE_DAYS_PARAM


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    drkds_login_history_purge_days = fields.Integer(
        string="Keep Login History (days)",
        config_parameter=PURGE_DAYS_PARAM,
        default=PURGE_DAYS_DEFAULT,
        help="The daily scheduled action deletes login records older than "
        "this many days. Set 0 to keep every record forever.",
    )
