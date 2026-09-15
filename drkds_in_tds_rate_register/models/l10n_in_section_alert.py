from odoo import fields, models


class L10nInSectionAlert(models.Model):
    """The localisation's TDS section, with a pointer to its rate map.

    Nothing about the section itself is changed here. The thresholds, the
    aggregation period, the alert text and the tax report line remain the
    localisation's business.
    """

    _inherit = "l10n_in.section.alert"

    drkds_rate_map_ids = fields.One2many(
        "drkds.tds.rate.map", "section_id", string="Rate Map",
        help="Which of this section's taxes to use, per company, "
        "depending on whether the vendor has a PAN.",
    )

    def _drkds_rate_map(self, company):
        """Return the rate map of this section for ``company``, or an empty set."""
        self.ensure_one()
        if not company:
            return self.env["drkds.tds.rate.map"]
        return self.env["drkds.tds.rate.map"].search([
            ("section_id", "=", self.id),
            ("company_id", "parent_of", company.id),
        ], limit=1)
