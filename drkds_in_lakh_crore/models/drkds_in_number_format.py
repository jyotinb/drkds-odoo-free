"""Indian digit grouping (lakh and crore) as a standalone utility.

The grouping rule: the first separator falls after three digits from the
right, every later separator after two. ``12345678`` therefore reads
``1,23,45,678`` - one crore twenty three lakh forty five thousand six hundred
and seventy eight.

Everything here works without touching a language record, so a report, an
export or a computed Char field can produce Indian grouping while the rest of
the database keeps its international format.
"""

from odoo import api, models

#: Odoo's ``res.lang.grouping`` value for Indian grouping. The trailing ``0``
#: means "repeat the previous count for the rest of the number", which is how
#: ``odoo.addons.base.models.res_lang.split`` reads it; a ``-1`` would instead
#: stop grouping and leave the head of a long number unseparated.
INDIAN_GROUPING = "[3,2,0]"

#: Odoo's default, ``1,234,567``.
INTERNATIONAL_GROUPING = "[3,0]"


def group_indian(value, digits=2, thousands_sep=",", decimal_point="."):
    """Return ``value`` as a string with Indian digit grouping.

    :param value: int, float or Decimal to format.
    :param digits: number of decimal places to keep; ``0`` gives an integer
        string with no decimal point.
    :param thousands_sep: separator placed between digit groups.
    :param decimal_point: separator placed before the decimal part.
    :return: str, for example ``group_indian(12345678) == '1,23,45,678.00'``.

    The sign is preserved and never separated from the number, and rounding is
    the same half-even rounding Python's ``%`` formatting uses.
    """
    digits = max(int(digits), 0)
    text = "%.*f" % (digits, value)

    sign = ""
    if text.startswith("-"):
        sign, text = "-", text[1:]
        if not float(text or 0):
            # "-0.00" reads as an error to a human; show plain zero.
            sign = ""

    if digits:
        whole, fraction = text.split(".")
    else:
        whole, fraction = text, ""

    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        # Walk the head two digits at a time, right to left.
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        groups.append(tail)
        whole = thousands_sep.join(groups)

    return sign + whole + (decimal_point + fraction if digits else "")


class DrkdsInNumberFormat(models.TransientModel):
    """Callable entry point for other modules and for server actions.

    Nothing is stored. The model exists so that Indian grouping is reachable
    through ``env`` from anywhere - a QWeb report, an automated action or
    another addon - without importing this module's Python.
    """

    _name = "drkds.in.number.format"
    _description = "Indian Number Format Helper"

    @api.model
    def group_indian(self, value, digits=2):
        """Group ``value`` using the current language's separators.

        Falls back to ``,`` and ``.`` when the language carries none.
        """
        lang = self.env["res.lang"]._lang_get(self.env.lang or "en_US")
        return group_indian(
            value,
            digits=digits,
            thousands_sep=lang.thousands_sep or ",",
            decimal_point=lang.decimal_point or ".",
        )

    @api.model
    def format_in_inr(self, amount, digits=2, symbol=True):
        """Return ``amount`` as an Indian-grouped rupee string.

        :param amount: the value to format.
        :param digits: decimal places, two by default as for paise.
        :param symbol: prefix the rupee sign.
        :return: str, for example ``'₹ 1,23,45,678.00'``.

        A negative amount keeps its minus sign in front of the symbol, which
        is how Indian statements print a credit balance.
        """
        grouped = self.group_indian(amount, digits=digits)
        if not symbol:
            return grouped
        if grouped.startswith("-"):
            return "-₹ " + grouped[1:]
        return "₹ " + grouped
