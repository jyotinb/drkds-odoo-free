from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DrkdsInStateCode(models.Model):
    """GST state code (the first two digits of a GSTIN)."""

    _name = "drkds.in.state.code"
    _description = "India GST State Code"
    _order = "code"
    _rec_name = "display_name"

    code = fields.Char(
        string="State Code", required=True, size=2,
        help="Two digit GST state code, for example 27 for Maharashtra.",
    )
    name = fields.Char(string="State Name", required=True, translate=True)
    state_id = fields.Many2one(
        "res.country.state", string="Odoo State",
        domain="[('country_id.code', '=', 'IN')]",
        help="Link to the Odoo state record so a partner address can be cross-checked "
        "against the state code inside its GSTIN.",
    )
    active = fields.Boolean(default=True)

    _code_uniq = models.Constraint(
        "unique(code)",
        "A GST state code may only be defined once.",
    )

    @api.depends("code", "name")
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.code} {record.name}" if record.code else record.name

    @api.constrains("code")
    def _check_code(self):
        for record in self:
            if not (record.code or "").isdigit() or len(record.code) != 2:
                raise ValidationError(
                    _("The GST state code %s must be exactly two digits.", record.code)
                )

    @api.model
    def _code_for_state(self, state):
        """Return the GST state code linked to an Odoo state, or False."""
        if not state:
            return False
        match = self.sudo().search([("state_id", "=", state.id)], limit=1)
        return match.code or False
