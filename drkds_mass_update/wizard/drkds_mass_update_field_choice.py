# Part of the drkds free suite for Odoo 19 Community. See LICENSE (LGPL-3).
"""The options the Mass Update wizard offers in its two pickers.

The fields a wizard may update depend on the model it was opened on, and the
choices of a selection-type field depend on the field picked in the first
step. Such per-record options cannot be a ``fields.Selection`` computed by a
method: the web client loads the form's field descriptions once per model,
with a context stripped down to ``lang`` and the ``*_view_ref`` keys, and
caches them, so the method never learns which wizard it is for and the
dropdown is empty in the browser.

So the options are records owned by the wizard, and the wizard's pickers are
Many2one fields to them with a domain on the wizard's id:

* ``field`` lines, one per field the user may update, created with the
  wizard;
* ``value`` lines, one per choice of a selection-type field, created when
  the field step is confirmed and dropped again by Back.

A line is only an offer. The wizard checks the chosen field against the
registry and the chosen value against the field's own choices before it
writes anything. Lines are created as the user, and each user sees only the
lines they created (record rule in ``security/drkds_mass_update_security.xml``),
exactly like the wizard itself.
"""
from odoo import fields, models


class DrkdsMassUpdateFieldChoice(models.TransientModel):
    """One option of one Mass Update wizard: a field, or a choice."""

    _name = "drkds.mass.update.field.choice"
    _description = "Mass Update Choice"
    _order = "sequence, id"
    _rec_names_search = ["name", "technical_name"]

    wizard_id = fields.Many2one(
        comodel_name="drkds.mass.update.wizard",
        string="Wizard",
        required=True,
        ondelete="cascade",
        index=True,
    )
    kind = fields.Selection(
        [("field", "Field"), ("value", "Choice")],
        string="Kind",
        required=True,
        help="Field: a field the wizard may update. Choice: one of the "
        "choices of the selection field being updated.",
    )
    sequence = fields.Integer(string="Sequence")
    name = fields.Char(string="Label", required=True)
    technical_name = fields.Char(
        string="Technical Name",
        required=True,
        help="The field name for a field, the stored key (as text) for a "
        "choice.",
    )
    field_type = fields.Char(string="Field Type")
    relation_model = fields.Char(string="Related Model")
