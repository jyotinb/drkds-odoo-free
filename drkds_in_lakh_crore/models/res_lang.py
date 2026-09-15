"""Switch a language between Indian and international digit grouping.

Odoo already knows both groupings: ``res.lang.grouping`` is a selection whose
values are read by ``res_lang.split`` when a number is formatted. This module
adds no new formatting engine - it gives the user a one click way to move a
language onto Indian grouping, a way back, and a live sample so the effect is
visible before the switch.

Nothing is applied on install. The language is only changed when a user asks
for it.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .drkds_in_number_format import INDIAN_GROUPING, INTERNATIONAL_GROUPING

#: The number shown in the sample field. Large enough to reach the crore group.
SAMPLE_VALUE = 123456789.5


class ResLang(models.Model):
    """Adds the Indian grouping switch to the language record."""

    _inherit = "res.lang"

    drkds_in_is_indian_grouping = fields.Boolean(
        string="Indian Grouping",
        compute="_compute_drkds_in_grouping_info",
        help="True when this language groups digits as 1,23,45,678 rather than "
        "123,456,789.",
    )
    drkds_in_grouping_sample = fields.Char(
        string="Grouping Sample",
        compute="_compute_drkds_in_grouping_info",
        help="How 123456789.50 is printed with this language's current settings.",
    )

    @api.depends("grouping", "thousands_sep", "decimal_point")
    def _compute_drkds_in_grouping_info(self):
        for lang in self:
            lang.drkds_in_is_indian_grouping = lang.grouping == INDIAN_GROUPING
            try:
                lang.drkds_in_grouping_sample = lang.format("%.2f", SAMPLE_VALUE, grouping=True)
            except (UserError, ValueError):
                # An inactive language has no formatting data cached.
                lang.drkds_in_grouping_sample = False

    def drkds_in_action_apply_indian_grouping(self):
        """Put the selected languages onto Indian (lakh and crore) grouping.

        Only the ``grouping`` field is touched. The decimal and thousands
        separators the user chose are left alone, so a language that separates
        with a space keeps doing so.
        """
        self._drkds_in_set_grouping(INDIAN_GROUPING)
        return self._drkds_in_notify(
            _("Indian grouping applied to %s language(s). Amounts now read 1,23,45,678.", len(self))
        )

    def drkds_in_action_restore_default_grouping(self):
        """Put the selected languages back onto international grouping."""
        self._drkds_in_set_grouping(INTERNATIONAL_GROUPING)
        return self._drkds_in_notify(
            _("International grouping restored on %s language(s).", len(self))
        )

    def _drkds_in_set_grouping(self, grouping):
        """Write ``grouping`` on the recordset, refusing an empty selection."""
        if not self:
            raise UserError(_("Select at least one language first."))
        self.write({"grouping": grouping})
        # Formatting data is cached per language; drop it so the change shows.
        self.env.registry.clear_cache('stable')

    def _drkds_in_notify(self, message):
        """Return a non-blocking confirmation toast."""
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Number Format"),
                "message": message,
                "type": "success",
                "sticky": False,
            },
        }
