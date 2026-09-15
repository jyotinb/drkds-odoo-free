from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Surface the wording preferences in Accounting > Settings.

    They sit next to Odoo's own 'Total amount of invoice in letters' switch,
    because that switch is what decides whether the sentence is printed at all.
    """

    _inherit = "res.config.settings"

    drkds_words_scale = fields.Selection(
        related="company_id.drkds_words_scale", readonly=False,
    )
    drkds_words_connector = fields.Char(
        related="company_id.drkds_words_connector", readonly=False,
    )
    drkds_words_suffix = fields.Char(
        related="company_id.drkds_words_suffix", readonly=False,
    )
    drkds_words_show_zero_subunit = fields.Boolean(
        related="company_id.drkds_words_show_zero_subunit", readonly=False,
    )
