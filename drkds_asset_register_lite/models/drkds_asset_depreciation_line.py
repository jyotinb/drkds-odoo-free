from odoo import api, fields, models


class DrkdsAssetDepreciationLine(models.Model):
    """One period of an asset's straight line depreciation schedule.

    Lines are derived data. They are rebuilt whenever an input changes and are
    never edited by hand, which is why the whole model is read only in the
    interface.
    """

    _name = "drkds.asset.depreciation.line"
    _description = "Asset Depreciation Line"
    _order = "asset_id, sequence"

    asset_id = fields.Many2one(
        "drkds.lite.asset", string="Asset", required=True, ondelete="cascade", index=True,
    )
    company_id = fields.Many2one(related="asset_id.company_id", store=True, index=True)
    currency_id = fields.Many2one(related="asset_id.currency_id")
    sequence = fields.Integer(string="Period", required=True, default=1)
    name = fields.Char(string="Period Label", compute="_compute_name")
    date_from = fields.Date(string="From", required=True)
    date_to = fields.Date(string="To", required=True)
    opening_value = fields.Monetary(string="Opening Value")
    depreciation = fields.Monetary(string="Depreciation")
    accumulated_depreciation = fields.Monetary(string="Accumulated Depreciation")
    closing_value = fields.Monetary(string="Closing Written Down Value")

    @api.depends("date_from", "date_to")
    def _compute_name(self):
        for line in self:
            if line.date_from and line.date_to:
                line.name = "%s - %s" % (
                    line.date_from.strftime("%d %b %Y"),
                    line.date_to.strftime("%d %b %Y"),
                )
            else:
                line.name = False
