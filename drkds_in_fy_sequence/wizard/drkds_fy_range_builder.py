from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DrkdsFyRangeBuilder(models.TransientModel):
    """Sets up financial year subsequences on a chosen sequence.

    Printing ``%(fy)s`` in a prefix changes what the number looks like; it does
    not change what the counter does. Only a date range per financial year
    makes the counter restart at one, which is what the GST rules ask for. This
    wizard creates those ranges.
    """

    _name = "drkds.fy.range.builder"
    _description = "Financial Year Range Builder"

    sequence_id = fields.Many2one(
        "ir.sequence", string="Sequence", required=True, ondelete="cascade",
        help="Sequence that should restart its counter every financial year.",
    )
    start_date = fields.Date(
        string="Start From", required=True, default=fields.Date.context_today,
        help="Any date inside the first financial year to create. The range "
        "created always covers the whole financial year, not just from this day.",
    )
    year_count = fields.Integer(
        string="Number of Years", required=True, default=3,
        help="How many consecutive financial years to create ranges for.",
    )
    company_id = fields.Many2one(
        "res.company", string="Company", related="sequence_id.drkds_fy_company_id", readonly=True,
    )
    preview = fields.Char(string="Preview", compute="_compute_preview")

    @api.depends("sequence_id", "start_date")
    def _compute_preview(self):
        """Show what a number drawn in the first financial year would look like."""
        for wizard in self:
            sequence = wizard.sequence_id
            if not sequence or not wizard.start_date:
                wizard.preview = False
                continue
            prefix, suffix = sequence.with_context(
                ir_sequence_date=wizard.start_date,
                ir_sequence_date_range=wizard.start_date,
            )._get_prefix_suffix()
            wizard.preview = "%s%s%s" % (prefix, "%%0%sd" % sequence.padding % 1, suffix)

    @api.constrains("year_count")
    def _check_year_count(self):
        for wizard in self:
            if wizard.year_count < 1:
                raise UserError(_("Ask for at least one financial year."))

    def action_build(self):
        """Create the ranges and show them."""
        self.ensure_one()
        ranges = self.sequence_id.drkds_build_fy_ranges(self.start_date, self.year_count)
        return {
            "type": "ir.actions.act_window",
            "name": _("Financial Year Ranges"),
            "res_model": "ir.sequence.date_range",
            "view_mode": "list",
            "domain": [("id", "in", ranges.ids)],
        }
