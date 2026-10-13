from odoo import api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    drkds_quality_check_ids = fields.One2many(
        "drkds.quality.check", "picking_id", string="Quality Checks",
    )
    drkds_quality_check_count = fields.Integer(
        string="Quality Check Count", compute="_compute_drkds_quality_counts",
    )
    drkds_quality_open_count = fields.Integer(
        string="Open Quality Checks", compute="_compute_drkds_quality_counts",
        help="Checks still to do or failed.",
    )

    @api.depends("drkds_quality_check_ids.state")
    def _compute_drkds_quality_counts(self):
        for picking in self:
            checks = picking.drkds_quality_check_ids
            picking.drkds_quality_check_count = len(checks)
            picking.drkds_quality_open_count = len(
                checks.filtered(lambda c: c.state != "pass")
            )

    def action_view_drkds_quality_checks(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "drkds_quality_lite.action_drkds_quality_check"
        )
        action["domain"] = [("picking_id", "=", self.id)]
        action["context"] = {
            "default_picking_id": self.id,
            "default_company_id": self.company_id.id,
        }
        if len(self.drkds_quality_check_ids) == 1:
            action["views"] = [(False, "form")]
            action["res_id"] = self.drkds_quality_check_ids.id
        return action

    def _drkds_quality_gate(self):
        """Refuse to go further while a blocking check is open or failed."""
        for picking in self:
            open_checks = picking.drkds_quality_check_ids.filtered(
                lambda c: c.blocking and c.state != "pass"
            )
            if open_checks:
                raise UserError(self.env._(
                    "%(picking)s cannot be validated: the following quality "
                    "checks must pass first.\n%(checks)s",
                    picking=picking.name,
                    checks="\n".join(
                        "- %s: %s (%s)" % (
                            c.name, c.point_id.name,
                            dict(c._fields["state"]._description_selection(self.env))[c.state],
                        ) for c in open_checks
                    ),
                ))

    def button_validate(self):
        # Fail fast, before any pre-validation wizard is shown. Draft
        # transfers are confirmed inside super and gated in _action_done.
        self.filtered(lambda p: p.state not in ("draft", "done"))._drkds_quality_gate()
        return super().button_validate()

    def _action_done(self):
        # Every path to done passes here, wizards included.
        self._drkds_quality_gate()
        return super()._action_done()
