from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DrkdsAssetCategory(models.Model):
    """A class of fixed assets carrying the defaults new assets start from.

    A category holds nothing more than defaults. Once an asset is created the
    figures live on the asset itself, so changing a category never silently
    rewrites the schedule of an asset that was already entered.
    """

    _name = "drkds.lite.asset.category"
    _description = "Fixed Asset Category"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char(
        help="Short code used as the prefix of the asset reference, for example VEH.",
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company,
    )
    method = fields.Selection(
        [("straight_line", "Straight Line")],
        string="Depreciation Method", required=True, default="straight_line",
        help="This register computes straight line depreciation only.",
    )
    period_type = fields.Selection(
        [("year", "Yearly"), ("month", "Monthly")],
        string="Period", required=True, default="year",
        help="Whether the schedule is broken into financial years or calendar months.",
    )
    useful_life_unit = fields.Selection(
        [("year", "Years"), ("month", "Months")],
        string="Useful Life Unit", required=True, default="year",
    )
    useful_life_value = fields.Integer(
        string="Useful Life", required=True, default=5,
        help="Expected life of the asset, expressed in the unit chosen alongside.",
    )
    salvage_percent = fields.Float(
        string="Salvage %", digits=(5, 2), default=0.0,
        help="Default residual value as a percentage of the purchase value. "
             "Used only to propose a figure; the asset keeps its own amount.",
    )
    asset_count = fields.Integer(compute="_compute_asset_count")

    _name_company_uniq = models.Constraint(
        "unique(name, company_id)",
        "An asset category of this name already exists for this company.",
    )

    def _compute_asset_count(self):
        counts = dict(
            self.env["drkds.lite.asset"]._read_group(
                [("category_id", "in", self.ids)], ["category_id"], ["__count"]
            )
        )
        for category in self:
            category.asset_count = counts.get(category, 0)

    @api.constrains("useful_life_value")
    def _check_useful_life_value(self):
        for category in self:
            if category.useful_life_value <= 0:
                raise ValidationError(
                    _("The useful life of category %s must be greater than zero.", category.name)
                )

    @api.constrains("salvage_percent")
    def _check_salvage_percent(self):
        for category in self:
            if not 0.0 <= category.salvage_percent < 100.0:
                raise ValidationError(
                    _("The salvage percentage must be zero or more and below one hundred.")
                )

    def action_view_assets(self):
        """Open the assets filed under this category."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Assets"),
            "res_model": "drkds.lite.asset",
            "view_mode": "list,form",
            "domain": [("category_id", "=", self.id)],
            "context": {"default_category_id": self.id},
        }
