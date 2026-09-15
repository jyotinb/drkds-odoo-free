from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..models.drkds_label_template import APPLIES_TO_MODEL

#: Models a user may start the wizard from, mapped to the record type whose
#: templates apply. ``product.template`` is offered as a convenience and is
#: resolved to its variants before printing.
SOURCE_MODELS = {
    "product.product": "product",
    "product.template": "product",
    "stock.lot": "lot",
    "stock.package": "package",
    "stock.picking": "picking",
}


class DrkdsLabelPrint(models.TransientModel):
    """Pick a label template and a number of copies, then print."""

    _name = "drkds.label.print"
    _description = "Print drkds Labels"

    template_id = fields.Many2one(
        "drkds.label.template", string="Label Template", required=True,
        domain="[('applies_to', '=', applies_to)]",
    )
    applies_to = fields.Selection(
        selection=lambda self: self.env["drkds.label.template"]._fields["applies_to"].selection,
        string="Record Type", required=True, readonly=True,
    )
    res_model = fields.Char(string="Source Model", required=True, readonly=True)
    res_ids_text = fields.Char(string="Source Records", required=True, readonly=True)
    quantity = fields.Integer(string="Copies", default=1, required=True)
    record_count = fields.Integer(compute="_compute_record_count")

    @api.depends("res_ids_text")
    def _compute_record_count(self):
        for wizard in self:
            wizard.record_count = len(wizard._record_ids())

    def _record_ids(self):
        self.ensure_one()
        return [int(value) for value in (self.res_ids_text or "").split(",") if value.strip().isdigit()]

    @api.model
    def default_get(self, fields_list):
        """Read the records the user launched the wizard from.

        ``product.template`` is translated to its variants here, because a label
        carries a barcode and a barcode belongs to a variant.
        """
        defaults = super().default_get(fields_list)
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids") or (
            [self.env.context["active_id"]] if self.env.context.get("active_id") else []
        )
        if not active_model or active_model not in SOURCE_MODELS:
            raise UserError(
                _("Labels cannot be printed from %s.", active_model or _("this screen"))
            )
        if not active_ids:
            raise UserError(_("Select at least one record to print."))

        records = self.env[active_model].browse(active_ids).exists()
        if active_model == "product.template":
            records = records.product_variant_ids
            if not records:
                raise UserError(_("These products have no variant to print."))
        applies_to = SOURCE_MODELS[active_model]

        defaults.update({
            "applies_to": applies_to,
            "res_model": APPLIES_TO_MODEL[applies_to],
            "res_ids_text": ",".join(str(record_id) for record_id in records.ids),
        })
        template = self.env["drkds.label.template"].search(
            [("applies_to", "=", applies_to)], limit=1,
        )
        if template:
            defaults.setdefault("template_id", template.id)
        return defaults

    def action_print(self):
        """Return the report action, with the template pinned in the context.

        The context is what carries the paper size through to the render, so a
        50 x 25 mm template prints on a 50 x 25 mm page.
        """
        self.ensure_one()
        if self.quantity < 1:
            raise UserError(_("Print at least one copy."))
        record_ids = self._record_ids()
        if not record_ids:
            raise UserError(_("There is nothing to print."))

        data = {
            "template_id": self.template_id.id,
            "res_model": self.res_model,
            "res_ids": record_ids,
            "quantity": self.quantity,
        }
        report = self.env.ref("drkds_label_designer_lite.action_report_drkds_label")
        action = report.with_context(
            drkds_label_template_id=self.template_id.id,
        ).report_action(self.template_id, data=data, config=False)
        action["close_on_report_download"] = True
        return action
