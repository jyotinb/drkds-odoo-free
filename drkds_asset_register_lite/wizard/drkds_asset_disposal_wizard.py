from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DrkdsAssetDisposalWizard(models.TransientModel):
    """Capture a disposal date and the proceeds, and close the asset off."""

    _name = "drkds.asset.disposal.wizard"
    _description = "Asset Disposal"

    asset_id = fields.Many2one("drkds.lite.asset", string="Asset", required=True, ondelete="cascade")
    currency_id = fields.Many2one(related="asset_id.currency_id")
    disposal_date = fields.Date(required=True, default=fields.Date.context_today)
    proceeds = fields.Monetary(string="Proceeds", default=0.0)
    scrapped = fields.Boolean(
        string="Scrapped",
        help="Tick when the asset was written off rather than sold. Proceeds are ignored.",
    )
    wdv_preview = fields.Monetary(
        string="Written Down Value", compute="_compute_wdv_preview",
        help="Book value on the disposal date, before the asset is closed off.",
    )
    gain_preview = fields.Monetary(string="Gain / Loss", compute="_compute_wdv_preview")

    @api.depends("asset_id", "disposal_date", "proceeds", "scrapped")
    def _compute_wdv_preview(self):
        for wizard in self:
            wdv = wizard.asset_id._wdv_as_at(wizard.disposal_date) if wizard.asset_id else 0.0
            wizard.wdv_preview = wdv
            wizard.gain_preview = (0.0 if wizard.scrapped else wizard.proceeds) - wdv

    def action_confirm(self):
        self.ensure_one()
        if self.disposal_date < self.asset_id.depreciation_start_date:
            raise UserError(_("The disposal date cannot fall before depreciation starts."))
        self.asset_id.action_dispose(
            disposal_date=self.disposal_date,
            proceeds=self.proceeds,
            scrapped=self.scrapped,
        )
        return {"type": "ir.actions.act_window_close"}
