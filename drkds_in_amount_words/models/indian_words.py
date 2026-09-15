"""Pure-python spelling of whole numbers in the Indian numbering system.

The Indian system groups digits as 2-2-3 rather than 3-3-3, so 12345678 is
written 1,23,45,678 and read "One Crore Twenty Three Lakh Forty Five Thousand
Six Hundred Seventy Eight".

Scale words used here
---------------------
========== ========== ==================
Word       Value      Example
========== ========== ==================
Thousand   10**3      1,000
Lakh       10**5      1,00,000
Crore      10**7      1,00,00,000
========== ========== ==================

**Above one crore this module keeps counting in crore.** 10**9 is spelled
"One Hundred Crore" and 10**11 is "Ten Thousand Crore". The alternative
convention -- arab (10**9), kharab (10**11), nil, padma -- is understood in
parts of north India but is almost never used on invoices, in bank drafts or
in company accounts, so it is deliberately not implemented. Anything above
one crore is expressed as a count of crore, recursively spelled with the very
same rules, which is what Indian auditors and banks expect to read.

Nothing in this file touches the ORM, so it can be imported and unit tested on
its own.
"""

#: Zero to nineteen, spelled out. Index 0 is empty on purpose: a zero digit
#: inside a larger number contributes no word at all.
ONES = (
    "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight",
    "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
    "Sixteen", "Seventeen", "Eighteen", "Nineteen",
)

#: Multiples of ten from twenty upward, indexed by the tens digit.
TENS = (
    "", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy",
    "Eighty", "Ninety",
)

ZERO = "Zero"
HUNDRED = "Hundred"

#: Divisor and word for each Indian group, largest first. The crore entry is
#: applied recursively, which is what produces "One Hundred Crore".
INDIAN_GROUPS = (
    (10 ** 7, "Crore"),
    (10 ** 5, "Lakh"),
    (10 ** 3, "Thousand"),
)


def _below_hundred(number):
    """Spell 1..99. Returns an empty string for 0."""
    if number < 20:
        return ONES[number]
    tens, units = divmod(number, 10)
    if units:
        return f"{TENS[tens]} {ONES[units]}"
    return TENS[tens]


def _below_thousand(number):
    """Spell 1..999 as "X Hundred Y". Returns an empty string for 0."""
    hundreds, rest = divmod(number, 100)
    words = []
    if hundreds:
        words.append(f"{ONES[hundreds]} {HUNDRED}")
    if rest:
        words.append(_below_hundred(rest))
    return " ".join(words)


def indian_words(number):
    """Spell a non-negative whole ``number`` in the Indian numbering system.

    :param int number: the value to spell. Must not be negative; the caller
        owns the sign, because the word for it depends on the document.
    :return: title-cased words, for example ``"One Crore Twenty Three Lakh"``.
    :rtype: str
    :raises ValueError: if ``number`` is negative.

    >>> indian_words(0)
    'Zero'
    >>> indian_words(100000)
    'One Lakh'
    >>> indian_words(1234567890)
    'One Hundred Twenty Three Crore Forty Five Lakh Sixty Seven Thousand Eight Hundred Ninety'
    """
    number = int(number)
    if number < 0:
        raise ValueError("indian_words() does not take negative numbers")
    if number == 0:
        return ZERO

    words = []
    remainder = number
    for divisor, label in INDIAN_GROUPS:
        count, remainder = divmod(remainder, divisor)
        if not count:
            continue
        # Crore is the top of the scale, so a count larger than 999 is spelled
        # with the full Indian rules again: 12345 crore, not "twelve thousand
        # three hundred forty five" flattened into the western scale.
        head = indian_words(count) if count > 999 else _below_thousand(count)
        words.append(f"{head} {label}")
    if remainder:
        words.append(_below_thousand(remainder))
    return " ".join(words)
