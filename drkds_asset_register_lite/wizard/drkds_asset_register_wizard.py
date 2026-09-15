from odoo import _, api, fields, models


class DrkdsAssetRegisterLine(models.TransientModel):
    """One row of a rendered asset register."""

    _name = "drkds.asset.register.line"
    _description = "Asset Register Line"
    _order = "category_name, code"

    wizard_id = fields.Many2one(
        "drkds.asset.register.wizard", required=True, ondelete="cascade", index=True,
    )
    asset_id = fields.Many2one("drkds.asset", string="Asset", ondelete="cascade")
    currency_id = fields.Many2one(related="wizard_id.currency_id")
    code = fields.Char(string="Reference")
    name = fields.Char(string="Description")
    category_name = fields.Char(string="Category")
    custodian_id = fields.Many2one("res.partner", string="Custodian")
    location = fields.Char()
    purchase_date = fields.Date()
    purchase_value = fields.Monetary()
    accumulated_depreciation = fields.Monetary()
    written_down_value = fields.Monetary(string="Written Down Value")
    state = fields.Char(string="Status")


class DrkdsAssetRegisterWizard(models.TransientModel):
    """Build a fixed asset register as at a chosen date.

    The register is the reason most people keep an asset list at all: what do we
    own, who holds it, and what is it worth on paper on a given day. The value
    is read out of the stored schedule and pro-rated inside the period the date
    falls in, so any date works, not only a period end.
    """

    _name = "drkds.asset.register.wizard"
    _description = "Asset Register"

    as_at_date = fields.Date(
        string="As At", required=True, default=fields.Date.context_today,
    )
    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    category_ids = fields.Many2many("drkds.asset.category", string="Categories")
    custodian_id = fields.Many2one("res.partner", string="Custodian")
    state_filter = fields.Selection(
        [
            ("active", "In Service"),
            ("all", "All"),
            ("closed", "Disposed and Scrapped"),
        ],
        string="Assets", default="active", required=True,
    )
    include_zero = fields.Boolean(
        string="Include Fully Depreciated",
        default=True,
        help="Untick to leave out assets already written down to their salvage value.",
    )
    line_ids = fields.One2many("drkds.asset.register.line", "wizard_id", readonly=True)

    def _asset_domain(self):
        self.ensure_one()
        domain = [("company_id", "=", self.company_id.id)]
        if self.state_filter == "active":
            domain.append(("state", "=", "running"))
        elif self.state_filter == "closed":
            domain.append(("state", "in", ("disposed", "scrapped")))
        else:
            domain.append(("state", "!=", "draft"))
        if self.category_ids:
            domain.append(("category_id", "in", self.category_ids.ids))
        if self.custodian_id:
            domain.append(("custodian_id", "=", self.custodian_id.id))
        domain.append(("purchase_date", "<=", self.as_at_date))
        return domain

    def _register_rows(self):
        """Return the register as a list of value dicts, newest category first."""
        self.ensure_one()
        currency = self.currency_id or self.env.company.currency_id
        rows = []
        for asset in self.env["drkds.asset"].search(self._asset_domain()):
            as_at = self.as_at_date
            if asset.disposal_date and asset.disposal_date < as_at:
                as_at = asset.disposal_date
            wdv = asset._wdv_as_at(as_at)
            if not self.include_zero and currency.is_zero(wdv - asset.salvage_value):
                continue
            rows.append({
                "asset_id": asset.id,
                "code": asset.code,
                "name": asset.name,
                "category_name": asset.category_id.name,
                "custodian_id": asset.custodian_id.id,
                "location": asset.location,
                "purchase_date": asset.purchase_date,
                "purchase_value": asset.purchase_value,
                "accumulated_depreciation": currency.round(asset.purchase_value - wdv),
                "written_down_value": wdv,
                "state": dict(asset._fields["state"].selection).get(asset.state),
            })
        return rows

    def action_view_register(self):
        """Materialise the register and show it as a list."""
        self.ensure_one()
        self.line_ids.unlink()
        self.env["drkds.asset.register.line"].create(
            [dict(row, wizard_id=self.id) for row in self._register_rows()]
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Asset Register as at %s", self.as_at_date),
            "res_model": "drkds.asset.register.line",
            "view_mode": "list",
            "domain": [("wizard_id", "=", self.id)],
            "context": {"create": False, "edit": False},
        }

    def action_print_register(self):
        self.ensure_one()
        self.line_ids.unlink()
        self.env["drkds.asset.register.line"].create(
            [dict(row, wizard_id=self.id) for row in self._register_rows()]
        )
        return self.env.ref(
            "drkds_asset_register_lite.action_report_asset_register"
        ).report_action(self)
