"""Minimal self-contained number-to-words helper, Indian numbering system.

The GST rules ask for the invoice value and the tax value to be spelled out on
the face of the invoice. Indian invoices spell amounts with the lakh/crore
grouping rather than the international million/billion grouping, so the stock
``num2words`` output is not what an Indian auditor expects.

This module deliberately carries no dependency. It is kept small on purpose:
it handles the range an invoice can realistically reach (up to
99,99,99,99,999) and the paise part, and nothing else.
"""

#: Words for 0..19, indexed directly.
_UNITS = (
    "Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight",
    "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
    "Sixteen", "Seventeen", "Eighteen", "Nineteen",
)

#: Words for the tens, indexed by the tens digit (index 0 and 1 unused).
_TENS = (
    "", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy",
    "Eighty", "Ninety",
)

#: Indian groupings, largest first: (divisor, label).
_SCALES = (
    (10 ** 7, "Crore"),
    (10 ** 5, "Lakh"),
    (10 ** 3, "Thousand"),
    (10 ** 2, "Hundred"),
)


def _below_hundred(number):
    """Return the words for an integer in the range 0..99."""
    if number < 20:
        return _UNITS[number]
    tens, units = divmod(number, 10)
    if units:
        return "%s %s" % (_TENS[tens], _UNITS[units])
    return _TENS[tens]


def integer_to_words(number):
    """Return the English words for a non-negative integer, Indian grouping.

    ``1234567`` becomes ``Twelve Lakh Thirty Four Thousand Five Hundred Sixty
    Seven``. Raises :class:`ValueError` for a negative input; callers are
    expected to deal with the sign themselves.
    """
    if number < 0:
        raise ValueError("integer_to_words expects a non-negative integer")
    if number < 100:
        return _below_hundred(int(number))

    parts = []
    remainder = int(number)
    for divisor, label in _SCALES:
        count, remainder = divmod(remainder, divisor)
        if count:
            parts.append("%s %s" % (integer_to_words(count), label))
    if remainder:
        parts.append(_below_hundred(remainder))
    return " ".join(parts)


def amount_to_words(amount, currency_label="Rupees", fraction_label="Paise"):
    """Spell a monetary amount the way an Indian tax invoice does.

    :param amount: the amount, positive or negative, as a float or Decimal.
    :param currency_label: name of the major unit, plural form.
    :param fraction_label: name of the minor unit, plural form.
    :return: a string such as ``Rupees One Thousand Two Hundred and Fifty
        Paise Only``. An amount with no fractional part omits the minor unit.
    """
    sign = "Minus " if amount < 0 else ""
    # round() on the product avoids 1.005 style float noise before splitting.
    total_paise = int(round(abs(float(amount)) * 100))
    major, minor = divmod(total_paise, 100)

    words = "%s %s" % (currency_label, integer_to_words(major))
    if minor:
        words += " and %s %s" % (integer_to_words(minor), fraction_label)
    return "%s%s Only" % (sign, words)
