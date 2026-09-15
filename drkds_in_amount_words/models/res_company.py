from odoo import fields, models


class ResCompany(models.Model):
    """Per-company wording preferences for the amount in words.

    The words end up on a printed, often legally meaningful document, so the
    phrasing is a company decision rather than a hard-coded string. Everything
    the wording engine needs beyond the currency itself lives here.
    """

    _inherit = "res.company"

    drkds_words_scale = fields.Selection(
        selection=[
            ("auto", "Indian scale for INR, international scale otherwise"),
            ("indian", "Indian scale for every currency"),
            ("international", "International scale for every currency"),
        ],
        string="Amount in Words Scale",
        default="auto",
        required=True,
        help="Which grouping the total is read in.\n"
        "Indian scale reads thousand, lakh and crore. International scale "
        "hands the job to Odoo's own converter, which reads thousand, "
        "million and billion.\n"
        "The default follows the currency: rupees are read the Indian way, "
        "everything else the international way.",
    )
    drkds_words_connector = fields.Char(
        string="Words Connector",
        default="and",
        help="Word placed between the whole part and the fractional part, as "
        "in 'Rupees Five Hundred and Fifty Paise Only'. Leave empty to join "
        "the two parts with nothing but a space.",
    )
    drkds_words_suffix = fields.Char(
        string="Words Suffix",
        default="Only",
        help="Word closing the sentence, as in '... Fifty Paise Only'. The "
        "suffix is what stops a figure being extended by hand on a printed "
        "document. Leave empty to print no suffix.",
    )
    drkds_words_show_zero_subunit = fields.Boolean(
        string="Spell Zero Paise",
        default=False,
        help="Print 'and Zero Paise' when the amount is a round figure. Off "
        "by default, which gives the shorter 'Rupees Five Hundred Only'. "
        "Some banks and government departments insist on the longer form.",
    )
