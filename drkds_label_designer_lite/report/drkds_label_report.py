from odoo import _, api, models
from odoo.exceptions import UserError


class ReportDrkdsLabel(models.AbstractModel):
    """Builds the list of labels to print.

    One entry per copy: the report template only iterates, so a quantity of
    five genuinely produces five labels rather than one label with a counter.
    """

    _name = "report.drkds_label_designer_lite.report_drkds_label"
    _description = "drkds Label Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        template = self.env["drkds.label.template"].browse(data.get("template_id") or docids or []).exists()
        if not template:
            raise UserError(_("No label template was given to print."))
        template.ensure_one()

        records = self.env[data["res_model"]].browse(data.get("res_ids") or []).exists()
        template._check_record_model(records)
        if not records:
            raise UserError(_("There is nothing to print."))

        quantity = max(1, int(data.get("quantity") or 1))
        labels = []
        for record in records:
            cells = template._render_cells(record)
            for _copy in range(quantity):
                labels.append({"record": record, "cells": cells})

        return {
            "doc_ids": template.ids,
            "doc_model": "drkds.label.template",
            "docs": template,
            "template": template,
            "page_style": template._page_style(),
            "labels": labels,
        }
