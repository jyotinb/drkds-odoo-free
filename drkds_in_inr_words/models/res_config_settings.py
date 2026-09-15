from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Surface the rupee wording options in Accounting > Settings.

    They sit directly under Odoo's own 'Total amount of invoice in letters'
    switch, because that switch is what decides whether the sentence is
    printed on an invoice at all.
    """

    _inherit = "res.config.settings"

    drkds_inr_words_enabled = fields.Boolean(
        related="company_id.drkds_inr_words_enabled", readonly=False,
    )
    drkds_inr_words_connector = fields.Char(
        related="company_id.drkds_inr_words_connector", readonly=False,
    )
    drkds_inr_words_suffix = fields.Char(
        related="company_id.drkds_inr_words_suffix", readonly=False,
    )
    drkds_inr_words_show_zero_paise = fields.Boolean(
        related="company_id.drkds_inr_words_show_zero_paise", readonly=False,
    )
