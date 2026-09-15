from odoo import fields, models


class ResCompany(models.Model):
    """Per-company control over the Indian reading of rupee amounts.

    The wording ends up on a document sent to a customer or handed to a bank,
    so the phrasing is a company decision rather than a hard-coded string.
    """

    _inherit = "res.company"

    drkds_inr_words_enabled = fields.Boolean(
        string="Indian Scale for Rupee Amounts",
        default=True,
        help="Read rupee amounts in lakh and crore wherever Odoo spells an "
        "amount out in words, whatever language the user is running.\n"
        "Switch it off to fall back to Odoo's behaviour, which follows the "
        "user's interface language and therefore reads millions and billions "
        "for anyone not running the English (IN) language.",
    )
    drkds_inr_words_connector = fields.Char(
        string="Words Connector",
        default="and",
        help="Word placed between the rupees and the paise, as in 'Rupees "
        "Five Hundred and Fifty Paise Only'. Leave empty to join the two "
        "parts with nothing but a space.",
    )
    drkds_inr_words_suffix = fields.Char(
        string="Words Suffix",
        default="Only",
        help="Word closing the sentence, as in '... Fifty Paise Only'. The "
        "suffix is what stops a printed figure being extended by hand. Leave "
        "empty to print no suffix.",
    )
    drkds_inr_words_show_zero_paise = fields.Boolean(
        string="Spell Zero Paise",
        default=False,
        help="Print 'and Zero Paise' when the amount is a round figure. Off "
        "by default, which gives the shorter 'Rupees Five Hundred Only'. "
        "Some banks and government departments insist on the longer form.",
    )
