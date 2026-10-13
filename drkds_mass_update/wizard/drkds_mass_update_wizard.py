# Part of the drkds free suite for Odoo 19 Community. See LICENSE (LGPL-3).
"""The Mass Update wizard.

Opened from the Actions menu of an enabled model's list view with the
selected records. Step one: pick the field. Step two: give it a value of the
matching kind, or tick Set Empty. Apply. The write runs as the current user,
never as superuser, in batches of 500. A batch refused by an access rule is
retried one record at a time, so the refused records are reported by name
and every other record is still updated.

Why two steps and no ``ir.model`` pickers: in Odoo 19 a plain internal user
has no read access on ``ir.model``, ``ir.model.fields`` or
``ir.model.fields.selection``, so a wizard built on Many2one fields to those
models is unusable by the very people it is for. Everything here comes from
the registry instead. The field list is a Selection computed from the model
named in the context, and the choices of a selection-type field are a
Selection computed from the field named in the context, which is why the
field is chosen first and the value second.
"""
from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.models import MAGIC_COLUMNS
from odoo.tools import split_every

#: Records written per ``write`` call.
BATCH_SIZE = 500

#: Context keys carrying the model and the chosen field between steps.
CTX_MODEL = "drkds_mup_model"
CTX_FIELD = "drkds_mup_field"

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
    field_name = fields.Selection(
        selection="_selection_field_name", string="Field to Update"
    )
    field_label = fields.Char(string="Field", compute="_compute_field_info")
    field_type = fields.Char(string="Field Type", compute="_compute_field_info")
    relation_model = fields.Char(
        string="Related Model", compute="_compute_field_info"
    )
    set_empty = fields.Boolean(
        string="Set Empty",
        help="Clear the field on every selected record instead of setting "
        "a value. Numbers become zero, a tag field loses all its tags.",
    )
    value_char = fields.Char(string="Text Value")
    value_text = fields.Text(string="Long Text Value")
    value_html = fields.Html(string="Formatted Text Value", sanitize=True)
    value_integer = fields.Integer(string="Whole Number Value")
    value_float = fields.Float(string="Number Value")
    value_boolean = fields.Boolean(string="Yes / No Value")
    value_date = fields.Date(string="Date Value")
    value_datetime = fields.Datetime(string="Date and Time Value")
    value_selection = fields.Selection(
        selection="_selection_value_selection", string="Choice"
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
    result_summary = fields.Html(string="Result", readonly=True, sanitize=False)

    # ------------------------------------------------------------------
    # Opening and stepping
    # ------------------------------------------------------------------

    @api.model
    def action_open_for(self, records):
        """Return the action that opens this wizard on ``records``.

        Called by the bound server action with the user's list selection.
        """
        return {
            "type": "ir.actions.act_window",
            "name": _("Mass Update"),
            "res_model": self._name,
            "view_mode": "form",
            "target": "new",
            "context": {
                CTX_MODEL: records._name,
                "default_model_name": records._name,
                "default_res_ids": ",".join(str(i) for i in records.ids),
            },
        }

    def _action_reopen(self):
        """Re-open this wizard, carrying the model and field in context so
        the dynamic selections keep their options."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Mass Update"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": {
                CTX_MODEL: self.model_name,
                CTX_FIELD: self.field_name,
            },
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

    def action_next(self):
        """Step one done: the field is chosen, ask for its value."""
        self.ensure_one()
        if not self.field_name:
            raise UserError(_("Choose the field to update."))
        self._check_field_allowed()
        self.write({"state": "value"})
        return self._action_reopen()

    def action_back(self):
        """Return to the field choice, dropping any value typed so far."""
        self.ensure_one()
        self.write({"state": "field", "set_empty": False, "value_selection": False,
                    "value_record_id": False})
        return self._action_reopen()

    # ------------------------------------------------------------------
    # Field list
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

    @api.model
    def _selection_field_name(self):
        return self._get_writable_fields(self.env.context.get(CTX_MODEL))

    @api.model
    def _selection_value_selection(self):
        model_name = self.env.context.get(CTX_MODEL)
        field_name = self.env.context.get(CTX_FIELD)
        if not model_name or model_name not in self.env or not field_name:
            return []
        field = self.env[model_name]._fields.get(field_name)
        if not field or field.type != "selection":
            return []
        described = self.env[model_name].fields_get([field_name], attributes=["selection"])
        return list(described.get(field_name, {}).get("selection") or [])

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
        return [int(i) for i in self.res_ids.split(",") if i.strip()]

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
                continue
            described = self.env[wizard.model_name].fields_get(
                [wizard.field_name], attributes=["string"]
            )
            wizard.field_label = described.get(wizard.field_name, {}).get("string") or field.string
            wizard.field_type = field.type
            wizard.relation_model = field.comodel_name or False

    # ------------------------------------------------------------------
    # The write
    # ------------------------------------------------------------------

    def _prepare_value(self):
        """The value to write, as the ORM expects it for the chosen field."""
        self.ensure_one()
        ftype = self.field_type
        if self.set_empty:
            if ftype in ("integer", "float", "monetary"):
                return 0
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
            if not self.value_selection:
                raise UserError(_("Pick a choice, or tick Set Empty to clear the field."))
            return self.value_selection
        if ftype in ("many2one", "many2many"):
            if not self.value_record_id:
                raise UserError(_("Pick a record, or tick Set Empty to clear the field."))
            target = self.env[self.relation_model].browse(self.value_record_id).exists()
            if not target:
                raise UserError(_("The chosen record no longer exists."))
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
        except AccessError:
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
        self._check_field_allowed()
        Model = self.env[self.model_name]
        # Model-level write access is a hard requirement; without it there is
        # nothing to report record by record.
        Model.check_access("write")
        records = Model.browse(self._get_res_ids()).exists()
        if not records:
            raise UserError(_("No record selected."))
        vals = {self.field_name: self._prepare_value()}
        updated, failures = self._write_batches(records, vals)
        self.write(
            {
                "state": "done",
                "updated_count": updated,
                "failed_count": len(failures),
                "result_summary": self._build_summary(updated, failures),
            }
        )
        return self._action_reopen()
