# Part of the drkds free suite for Odoo 19 Community. See LICENSE (LGPL-3).
"""Models on which mass update is allowed.

Odoo cannot bind one server action to every model at once: a bound action
(``binding_model_id``) belongs to exactly one model. So the administrator
lists the models here, and each enabled line owns one ``ir.actions.server``
bound to that model's list view. Enabling creates the action, disabling or
deleting the line removes it, and the uninstall hook removes whatever is left.

The action itself only opens the wizard. Nothing is written from here.
"""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

#: What the bound action runs. ``records`` is the selection the user made in
#: the list view; the wizard works out the rest from it.
SERVER_ACTION_CODE = (
    'action = env["drkds.mass.update.wizard"].action_open_for(records)'
)


class DrkdsMassUpdateModel(models.Model):
    """One line per model, carrying the bound action while enabled."""

    _name = "drkds.mass.update.model"
    _description = "Mass Update Enabled Model"
    _order = "model_name"
    _rec_name = "model_name"

    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
        domain=[("transient", "=", False)],
        help="The model whose list view gets the Mass update action.",
    )
    model_name = fields.Char(
        related="model_id.model", string="Technical Name", store=True
    )
    model_display_name = fields.Char(
        related="model_id.name", string="Model Name"
    )
    enabled = fields.Boolean(
        string="Enabled",
        default=True,
        help="Enabled: the Mass update action is present on the list view "
        "of this model. Disabled: the action is removed, the line is kept.",
    )
    server_action_id = fields.Many2one(
        comodel_name="ir.actions.server",
        string="Bound Action",
        readonly=True,
        ondelete="set null",
        help="The server action bound to the model's list view while the "
        "line is enabled. Created and removed automatically.",
    )

    _model_uniq = models.Constraint(
        "unique(model_id)", "This model is already listed. Enable it instead."
    )

    @api.constrains("model_id")
    def _check_model_is_regular(self):
        """Only a persisted, non-transient model with a list view makes sense."""
        for line in self:
            if line.model_id.transient:
                raise ValidationError(
                    _("%s is a wizard model and cannot be mass updated.")
                    % line.model_id.name
                )
            if line.model_id.model not in self.env:
                raise ValidationError(
                    _("Model %s is not loaded in this database.")
                    % line.model_id.model
                )

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._drkds_sync_server_action()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if "enabled" in vals or "model_id" in vals:
            self._drkds_sync_server_action()
        return res

    def unlink(self):
        self._drkds_remove_server_action()
        return super().unlink()

    def _drkds_server_action_values(self):
        """Values for the bound action of this line."""
        self.ensure_one()
        return {
            "name": _("Mass update"),
            "model_id": self.model_id.id,
            "state": "code",
            "code": SERVER_ACTION_CODE,
            "binding_model_id": self.model_id.id,
            "binding_type": "action",
            "binding_view_types": "list",
            # Any internal user may open the wizard. The wizard itself then
            # checks write access on the model and applies the record rules
            # record by record, which is what lets it report a refused record
            # instead of failing the whole selection up front.
            "group_ids": [fields.Command.set([self.env.ref("base.group_user").id])],
        }

    def _drkds_sync_server_action(self):
        """Make the bound action match the line: present iff enabled."""
        for line in self:
            action = line.server_action_id
            if line.enabled:
                values = line._drkds_server_action_values()
                if action:
                    action.write(values)
                else:
                    line.server_action_id = self.env["ir.actions.server"].create(values)
            elif action:
                line._drkds_remove_server_action()

    def _drkds_remove_server_action(self):
        """Delete the bound actions of these lines, if any."""
        actions = self.server_action_id
        if actions:
            self.write({"server_action_id": False})
            actions.unlink()

    def action_enable(self):
        self.write({"enabled": True})
        return True

    def action_disable(self):
        self.write({"enabled": False})
        return True
