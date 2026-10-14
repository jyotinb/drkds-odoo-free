# Part of the drkds free suite for Odoo 19 Community. See LICENSE (LGPL-3).
"""The Mass Update wizard.

Opened from the Actions menu of an enabled model's list view with the
selected records. Step one: pick the field. Step two: give it a value of the
matching kind, or tick Set Empty. Apply. The write runs as the current user,
never as superuser, in batches of 500. A batch refused by an access rule is
retried one record at a time, so the refused records are reported by name
and every other record is still updated.

The wizard runs only on models the administrator enabled, and each wizard is
visible to the user who opened it only (see the record rule in
``security/drkds_mass_update_security.xml``): the stored model, records,
field and value are what the write uses, so nobody else may change them.

Why the pickers point at choice lines of the wizard's own: in Odoo 19 a
plain internal user has no read access on ``ir.model``, ``ir.model.fields``
or ``ir.model.fields.selection``, so a wizard built on Many2one fields to
those models is unusable by the very people it is for. And a Selection whose
options a method computes from a context key is empty in the browser, which
sends ``get_views`` no such key. So the wizard reads the fields and choices
from the registry and stores them as ``drkds.mass.update.field.choice``
lines it owns: the field lines when it is created (``action_open_for``
creates it before the dialog opens, so the lines exist when the form loads),
the choices of a selection-type field when the field step is confirmed,
which is why the field is chosen first and the value second.
"""
from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.models import MAGIC_COLUMNS
from odoo.tools import split_every

#: Records written per ``write`` call.
BATCH_SIZE = 500

#: Field types the wizard knows how to take a value for. Anything else is
#: left out of the field list rather than offered with no way to fill it.
SUPPORTED_TYPES = (
    "char",
    "text",
    "html",
    "integer",
    "float",
    "monetary",
    "boolean",
    "date",
    "datetime",
    "selection",
    "many2one",
    "many2many",
)


class DrkdsMassUpdateWizard(models.TransientModel):
    """One field, one value, many records."""

    _name = "drkds.mass.update.wizard"
    _description = "Mass Update"

    model_name = fields.Char(string="Model", required=True, readonly=True)
    model_description = fields.Char(
        string="Records", compute="_compute_model_description"
    )
    res_ids = fields.Char(
        string="Record Ids", readonly=True,
        help="Comma-separated ids of the selected records.",
    )
    record_count = fields.Integer(
        string="Selected Records", compute="_compute_record_count"
    )
    choice_ids = fields.One2many(
        comodel_name="drkds.mass.update.field.choice",
        inverse_name="wizard_id",
        string="Choices",
    )
    # String domains: they only guide the picker. The chosen line is checked
    # again (field_name below, _prepare_value) before anything is written.
    field_choice_id = fields.Many2one(
        comodel_name="drkds.mass.update.field.choice",
        string="Field to Update",
        domain="[('wizard_id', '=', id), ('kind', '=', 'field')]",
    )
    field_name = fields.Char(
        string="Technical Field Name",
        compute="_compute_field_name",
        store=True,
    )
    field_label = fields.Char(string="Field", compute="_compute_field_info")
    field_type = fields.Char(string="Field Type", compute="_compute_field_info")
    relation_model = fields.Char(
        string="Related Model", compute="_compute_field_info"
    )
    field_required = fields.Boolean(
        string="Field Required", compute="_compute_field_info"
    )
    set_empty = fields.Boolean(
        string="Set Empty",
        help="Clear the field on every selected record instead of setting "
        "a value. Numbers become zero, a tag field loses all its tags. Not "
        "available on a required field.",
    )
    value_char = fields.Char(string="Text Value")
    value_text = fields.Text(string="Long Text Value")
    value_html = fields.Html(string="Formatted Text Value", sanitize=True)
    value_integer = fields.Integer(string="Whole Number Value")
    value_float = fields.Float(string="Number Value")
    value_boolean = fields.Boolean(string="Yes / No Value")
    value_date = fields.Date(string="Date Value")
    value_datetime = fields.Datetime(string="Date and Time Value")
    value_choice_id = fields.Many2one(
        comodel_name="drkds.mass.update.field.choice",
        string="Choice",
        domain="[('wizard_id', '=', id), ('kind', '=', 'value')]",
    )
    value_record_id = fields.Many2oneReference(
        string="Record", model_field="relation_model"
    )
    state = fields.Selection(
        [("field", "Field"), ("value", "Value"), ("done", "Done")],
        default="field", readonly=True,
    )
    updated_count = fields.Integer(string="Updated", readonly=True)
    failed_count = fields.Integer(string="Not Updated", readonly=True)
    # Sanitized like any user-writable html field: the summary is built from
    # escaped markup, so sanitizing keeps it intact while refusing live
    # markup sent straight over RPC.
    result_summary = fields.Html(string="Result", readonly=True)

    # ------------------------------------------------------------------
    # Opening and stepping
    # ------------------------------------------------------------------

    @api.model
    def action_open_for(self, records):
        """Create the wizard on ``records`` and return the action opening it.

        Called by the bound server action with the user's list selection.
        The wizard is created here, before the dialog opens, rather than by
        the dialog's first button: its pickers offer the wizard's own choice
        lines (domain on the wizard's id), so the record and its field lines
        must exist when the form loads.
        """
        wizard = self.create({
            "model_name": records._name,
            "res_ids": ",".join(str(i) for i in records.ids),
        })
        return wizard._action_reopen()

    def _action_reopen(self):
        """The action showing this wizard, at whatever step it is."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Mass Update"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    @api.model
    def default_get(self, fields_list):
        """Fall back on the usual active_model / active_ids when opened
        without explicit defaults, for instance from a test or a shell."""
        res = super().default_get(fields_list)
        ctx = self.env.context
        if not res.get("model_name") and ctx.get("active_model"):
            res["model_name"] = ctx["active_model"]
        if not res.get("res_ids") and ctx.get("active_ids"):
            res["res_ids"] = ",".join(str(i) for i in ctx["active_ids"])
        return res

    @api.model_create_multi
    def create(self, vals_list):
        wizards = super().create(vals_list)
        wizards._populate_field_choices()
        return wizards

    def write(self, vals):
        res = super().write(vals)
        # The field lines belong to the model; the form never changes it,
        # but a direct call may, and the offer must follow.
        if "model_name" in vals:
            self._populate_field_choices()
        return res

    def action_next(self):
        """Step one done: the field is chosen, ask for its value."""
        self.ensure_one()
        if not self.field_name:
            raise UserError(_("Choose the field to update."))
        self._check_model_enabled()
        self._check_field_allowed()
        self.write({"state": "value", "value_choice_id": False})
        self._populate_value_choices()
        return self._action_reopen()

    def action_back(self):
        """Return to the field choice, dropping any value typed so far."""
        self.ensure_one()
        self.write({"state": "field", "set_empty": False, "value_choice_id": False,
                    "value_record_id": False})
        self._get_choices("value").unlink()
        return self._action_reopen()

    # ------------------------------------------------------------------
    # Field list and choice lines
    # ------------------------------------------------------------------

    @api.model
    def _get_writable_fields(self, model_name):
        """``[(name, label)]`` of the fields the wizard may offer, by label.

        Kept: stored, writable fields of a supported type. Left out: the id
        and the create/write audit columns, non-stored fields, readonly
        fields, binary and one2many fields (unsupported types), and fields
        restricted to groups the current user lacks.

        A computed field is readonly unless it has an inverse or is declared
        ``readonly=False``; the ORM sets that flag, so the readonly test is
        what excludes a computed field without an inverse while keeping one
        Odoo itself lets the user write, such as a stored salesperson that is
        only precomputed from the parent.
        """
        if not model_name or model_name not in self.env:
            return []
        Model = self.env[model_name]
        names = []
        for name, field in Model._fields.items():
            if name in MAGIC_COLUMNS:
                continue
            if not field.store or field.readonly:
                continue
            if field.type not in SUPPORTED_TYPES:
                continue
            if field.groups and not self.env.user.has_groups(field.groups):
                continue
            names.append(name)
        # fields_get gives the translated label and, as a second guard,
        # drops any field the user may not access.
        described = Model.fields_get(names, attributes=["string"])
        result = [(name, described[name]["string"]) for name in names if name in described]
        result.sort(key=lambda item: (item[1].lower(), item[0]))
        return result

    @api.model
    def _get_writable_field_names(self, model_name):
        return [name for name, _label in self._get_writable_fields(model_name)]

    def _get_choices(self, kind):
        """This wizard's choice lines of ``kind`` ("field" or "value")."""
        return self.choice_ids.filtered(lambda choice: choice.kind == kind)

    def _populate_field_choices(self):
        """(Re)build the field lines: one per field the user may update,
        in the order of ``_get_writable_fields`` (by label)."""
        self._get_choices("field").unlink()
        vals_list = []
        for wizard in self:
            if wizard.model_name not in self.env:
                continue
            model_fields = self.env[wizard.model_name]._fields
            for sequence, (name, label) in enumerate(
                wizard._get_writable_fields(wizard.model_name)
            ):
                field = model_fields[name]
                vals_list.append({
                    "wizard_id": wizard.id,
                    "kind": "field",
                    "sequence": sequence,
                    "name": label,
                    "technical_name": name,
                    "field_type": field.type,
                    "relation_model": field.comodel_name or False,
                })
        self.env["drkds.mass.update.field.choice"].create(vals_list)

    def _populate_value_choices(self):
        """(Re)build the value lines: the choices of the chosen field when it
        is a selection, none otherwise. Labels come translated from
        ``fields_get``; keys are kept as text, as a form sends them."""
        self.ensure_one()
        self._get_choices("value").unlink()
        if self.field_type != "selection":
            return
        described = self.env[self.model_name].fields_get(
            [self.field_name], attributes=["selection"]
        )
        options = described.get(self.field_name, {}).get("selection") or []
        self.env["drkds.mass.update.field.choice"].create([
            {
                "wizard_id": self.id,
                "kind": "value",
                "sequence": sequence,
                "name": label,
                "technical_name": str(key),
            }
            for sequence, (key, label) in enumerate(options)
        ])

    def _check_model_enabled(self):
        """Refuse a model the administrator has not enabled.

        The bound action only exists on enabled models, but the wizard can
        be created over RPC for any model name; the administrator's list is
        only a control if the wizard itself enforces it.
        """
        self.ensure_one()
        enabled = self.env["drkds.mass.update.model"].search_count(
            [("model_name", "=", self.model_name), ("enabled", "=", True)], limit=1
        )
        if not enabled:
            raise UserError(
                _("Mass update is not enabled for %s. An administrator can enable "
                  "it under Settings > Technical > Mass Update.")
                % (self.model_description or self.model_name)
            )

    def _check_field_allowed(self):
        self.ensure_one()
        if self.field_name not in self._get_writable_field_names(self.model_name):
            raise UserError(
                _("The field %s cannot be mass updated.") % (self.field_label or self.field_name)
            )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------

    def _get_res_ids(self):
        self.ensure_one()
        if not self.res_ids:
            return []
        # Each record once, in selection order.
        return list(dict.fromkeys(int(i) for i in self.res_ids.split(",") if i.strip()))

    @api.depends("res_ids")
    def _compute_record_count(self):
        for wizard in self:
            wizard.record_count = len(wizard._get_res_ids())

    @api.depends("model_name")
    def _compute_model_description(self):
        for wizard in self:
            if wizard.model_name and wizard.model_name in self.env:
                wizard.model_description = self.env[wizard.model_name]._description
            else:
                wizard.model_description = wizard.model_name

    @api.depends("field_choice_id.kind", "field_choice_id.technical_name",
                 "field_choice_id.wizard_id")
    def _compute_field_name(self):
        """The technical name of the picked field line. A line of any other
        wizard, or a value line, gives no field: the picker's domain is only
        a guide, a direct call can send any id. (``_origin``: the form's
        onchange computes on a copy of the wizard.)"""
        for wizard in self:
            choice = wizard.field_choice_id
            own = choice.kind == "field" and choice.wizard_id._origin == wizard._origin
            wizard.field_name = choice.technical_name if own else False

    @api.depends("model_name", "field_name")
    @api.depends_context("uid", "lang")
    def _compute_field_info(self):
        for wizard in self:
            field = False
            if wizard.model_name in self.env and wizard.field_name:
                field = self.env[wizard.model_name]._fields.get(wizard.field_name)
            if not field:
                wizard.field_label = False
                wizard.field_type = False
                wizard.relation_model = False
                wizard.field_required = False
                continue
            described = self.env[wizard.model_name].fields_get(
                [wizard.field_name], attributes=["string"]
            )
            wizard.field_label = described.get(wizard.field_name, {}).get("string") or field.string
            wizard.field_type = field.type
            wizard.relation_model = field.comodel_name or False
            wizard.field_required = bool(field.required)

    # ------------------------------------------------------------------
    # The write
    # ------------------------------------------------------------------

    def _prepare_value(self):
        """The value to write, as the ORM expects it for the chosen field."""
        self.ensure_one()
        ftype = self.field_type
        field = self.env[self.model_name]._fields[self.field_name]
        if self.set_empty:
            if ftype in ("integer", "float", "monetary"):
                return 0
            if ftype == "boolean":
                return False
            # The form never lets a required field be emptied; the database
            # would refuse it with a NOT NULL error.
            if field.required:
                raise UserError(
                    _("%s is a required field and cannot be emptied.") % self.field_label
                )
            if ftype == "many2many":
                return [fields.Command.clear()]
            return False
        if ftype in ("char", "text", "html"):
            value = {
                "char": self.value_char,
                "text": self.value_text,
                "html": self.value_html,
            }[ftype]
            if not value:
                raise UserError(_("Enter a value, or tick Set Empty to clear the field."))
            return value
        if ftype == "integer":
            return self.value_integer
        if ftype in ("float", "monetary"):
            return self.value_float
        if ftype == "boolean":
            return self.value_boolean
        if ftype == "date":
            if not self.value_date:
                raise UserError(_("Pick a date, or tick Set Empty to clear the field."))
            return self.value_date
        if ftype == "datetime":
            if not self.value_datetime:
                raise UserError(_("Pick a date and time, or tick Set Empty to clear the field."))
            return self.value_datetime
        if ftype == "selection":
            choice = self.value_choice_id
            if not choice:
                raise UserError(_("Pick a choice, or tick Set Empty to clear the field."))
            # The picker offers this wizard's own choice lines only, but a
            # direct call can send any line id: take only a value line of
            # this wizard (read as the user, so another user's line is not
            # even read).
            if choice not in self._get_choices("value"):
                raise UserError(
                    _("This choice is not offered for %s.") % self.field_label
                )
            # A line can also be crafted, and the ORM does not validate a
            # selection whose choices come from a method (res.partner.lang,
            # tz, ...): check the key against the field itself. Keys are
            # matched as text, as the lines store them.
            choices = {str(key): key for key in field.get_values(self.env)}
            if choice.technical_name not in choices:
                raise UserError(
                    _("%(value)s is not a valid choice for %(field)s.",
                      value=choice.name, field=self.field_label)
                )
            return choices[choice.technical_name]
        if ftype in ("many2one", "many2many"):
            if not self.value_record_id:
                raise UserError(_("Pick a record, or tick Set Empty to clear the field."))
            target = self.env[self.relation_model].browse(self.value_record_id).exists()
            if not target:
                raise UserError(_("The chosen record no longer exists."))
            # The picker only offers records the user can read; refuse any
            # other id, such as a record of a company the user is not in.
            target.check_access("read")
            if ftype == "many2one":
                return target.id
            return [fields.Command.link(target.id)]
        raise UserError(_("Fields of type %s cannot be mass updated.") % ftype)

    def _write_batches(self, records, vals):
        """Write ``vals`` on ``records`` in batches, as the current user.

        Returns ``(updated_count, failures)`` where ``failures`` is a list of
        ``(record, message)`` for every record an access rule refused. A
        batch that fails is retried record by record, so only the refused
        records are left out. Each attempt runs in a savepoint, so a refused
        write leaves no half-applied change and no stale cache behind.
        """
        updated = 0
        failures = []
        for batch_ids in split_every(BATCH_SIZE, records.ids):
            batch = records.browse(batch_ids)
            try:
                with self.env.cr.savepoint():
                    batch.write(vals)
                updated += len(batch)
                continue
            except AccessError:
                pass
            for record in batch:
                try:
                    with self.env.cr.savepoint():
                        record.write(vals)
                    updated += 1
                except AccessError as error:
                    failures.append((record, error.args[0] if error.args else ""))
        return updated, failures

    @api.model
    def _describe_record(self, record):
        """Display name when readable, else the id, never an error."""
        try:
            return record.display_name or "#%d" % record.id
        except (AccessError, MissingError):
            return "#%d" % record.id

    def _build_summary(self, updated, failures):
        parts = [
            Markup("<p>%s</p>")
            % _("%(done)d record(s) updated, %(failed)d not updated.",
                done=updated, failed=len(failures))
        ]
        if failures:
            items = Markup("").join(
                Markup("<li><strong>%s</strong> (id %d)<br/><small>%s</small></li>")
                % (self._describe_record(record), record.id,
                   escape(message).replace("\n", Markup("<br/>")))
                for record, message in failures
            )
            parts.append(
                Markup("<p>%s</p><ul>%s</ul>")
                % (_("Records that could not be updated:"), items)
            )
        return Markup("").join(parts)

    def action_apply(self):
        """Write the value on every selected record and show the result."""
        self.ensure_one()
        if not self.field_name:
            raise UserError(_("Choose the field to update."))
        if self.model_name not in self.env:
            raise UserError(_("Model %s is not loaded in this database.") % self.model_name)
        self._check_model_enabled()
        self._check_field_allowed()
        Model = self.env[self.model_name]
        # Model-level write access is a hard requirement; without it there is
        # nothing to report record by record.
        Model.check_access("write")
        selected = Model.browse(self._get_res_ids())
        if not selected:
            raise UserError(_("No record selected."))
        vals = {self.field_name: self._prepare_value()}
        # A record deleted since the selection was made is reported, so the
        # updated and not-updated counts always add up to the selection.
        records = selected.exists()
        updated, failures = self._write_batches(records, vals)
        failures += [
            (record, _("This record no longer exists."))
            for record in selected - records
        ]
        self.write(
            {
                "state": "done",
                "updated_count": updated,
                "failed_count": len(failures),
                "result_summary": self._build_summary(updated, failures),
            }
        )
        return self._action_reopen()
