import logging

from odoo import models

try:
    from num2words import num2words
except ImportError:
    num2words = None

_logger = logging.getLogger(__name__)

#: The num2words locale that reads numbers in the Indian 2-2-3 grouping:
#: thousand, lakh, crore, and crore again above that. num2words is already a
#: hard dependency of Odoo, so nothing new is pulled in.
INDIAN_LANG = "en_IN"

#: Currency whose amounts are read on the Indian scale. Keyed off the currency
#: being printed, deliberately: not the user's language, and not the company's
#: country. A Singapore company invoicing an Indian customer in rupees still
#: has to write the rupee amount the way an Indian bank reads it.
INR = "INR"

#: Fallback names for when the currency record carries no unit labels, which
#: is how Odoo ships them. "Indian Rupee One Lakh" reads badly, so the plural
#: is used. Labels set on the currency always win.
DEFAULT_UNIT_LABEL = "Rupees"
DEFAULT_SUBUNIT_LABEL = "Paise"


class ResCurrency(models.Model):
    """Make Odoo's amount-to-text follow the currency, not the user language.

    Odoo already spells amounts out in words. It does so through
    :meth:`amount_to_text`, which calls ``num2words`` with the ISO code of the
    *user's interface language*. ``num2words`` genuinely knows the Indian
    scale, under the ``en_IN`` locale, so a user running English (IN) already
    gets "One Lakh" for free.

    The problem is that almost every Indian business runs Odoo in plain
    English (US). For them the same rupee invoice silently prints "One Hundred
    Thousand" and "Ten Million" - on a document that goes to a customer and
    sometimes to a bank. The interface language has nothing to do with the
    currency being printed, so keying the scale off it is wrong for India.

    This override narrows that decision: when the currency is INR and the
    company has not turned the feature off, the amount is read with the
    ``en_IN`` locale whatever language the user is running. Every other
    currency is handed straight back to ``super()``, untouched.

    Because the override sits on ``amount_to_text`` itself, every core caller
    is corrected at once - the invoice total in letters on ``account.move``
    and the amount in words on a printed cheque in ``account_check_printing``.
    """

    _inherit = "res.currency"

    # -- the override --------------------------------------------------
    def amount_to_text(self, amount):
        """Spell ``amount`` out, on the Indian scale when the currency is INR.

        :param float amount: the value to spell.
        :return: the amount in words. Non-rupee currencies, and rupee amounts
            in a company that has switched the feature off, get exactly what
            Odoo would have returned.
        :rtype: str
        """
        self.ensure_one()
        if not self._drkds_inr_words_active():
            return super().amount_to_text(amount)
        return self.drkds_amount_in_words(amount)

    # -- public helper -------------------------------------------------
    def drkds_amount_in_words(self, amount, company=None):
        """Return ``amount`` read on the Indian scale, with paise and suffix.

        Usable directly from a QWeb report for any amount that is not the
        document total - a tax amount, a round-off, an advance - where core
        offers nothing.

        :param float amount: the value to spell. A negative amount is prefixed
            with "Minus"; the digits are always spelled positively.
        :param company: company whose wording preferences apply. Defaults to
            the environment's company.
        :return: a finished sentence such as
            ``"Rupees Five Hundred and Fifty Paise Only"``.
        :rtype: str
        """
        self.ensure_one()
        company = company or self.env.company
        amount = float(amount or 0.0)
        negative = amount < 0
        integral, _sep, fractional = f"{abs(amount):.{self.decimal_places}f}".partition(".")

        words = []
        if negative:
            words.append(self.env._("Minus"))
        words.append(self.currency_unit_label or DEFAULT_UNIT_LABEL)
        words.append(self._drkds_indian_words(int(integral)))

        paise = int(fractional or 0)
        if self.decimal_places and (paise or company.drkds_inr_words_show_zero_paise):
            connector = (company.drkds_inr_words_connector or "").strip()
            if connector:
                words.append(connector)
            words.append(self._drkds_indian_words(paise))
            words.append(self.currency_subunit_label or DEFAULT_SUBUNIT_LABEL)

        suffix = (company.drkds_inr_words_suffix or "").strip()
        if suffix:
            words.append(suffix)
        return " ".join(part for part in words if part)

    # -- internals -----------------------------------------------------
    def _drkds_inr_words_active(self, company=None):
        """Tell whether this currency should be read on the Indian scale.

        Three things must hold: the currency is the rupee, the company has the
        feature on, and ``num2words`` is importable. The last one matters
        because core degrades to an empty string without it, and silently
        taking that path over here would look like a bug in this module.
        """
        self.ensure_one()
        if num2words is None:
            return False
        company = company or self.env.company
        return self.name == INR and company.drkds_inr_words_enabled

    def _drkds_indian_words(self, number):
        """Spell a non-negative whole ``number`` with the ``en_IN`` locale.

        ``num2words`` separates the Indian groups with commas, as in
        "Twelve Lakh, Thirty-Four Thousand". Those commas are stripped here
        for the same reason ``account.move`` strips them from its own field:
        a sentence on a legal document should not carry list punctuation.
        """
        try:
            words = num2words(int(number), lang=INDIAN_LANG)
        except NotImplementedError:  # pragma: no cover - en_IN ships with num2words
            _logger.warning("num2words has no %s locale, falling back to en", INDIAN_LANG)
            words = num2words(int(number), lang="en")
        return words.title().replace(",", "")
