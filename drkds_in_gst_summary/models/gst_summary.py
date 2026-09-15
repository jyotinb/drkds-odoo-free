"""Period GST summary: outward, inward and HSN, for checking before filing.

Design note - why a transient model rather than a stored report
---------------------------------------------------------------
The screen is a transient (wizard) model that also holds its own result rows.
Three reasons:

* A GST summary is derived data. Storing it would create a second source of
  truth that goes stale the moment somebody posts a back-dated invoice or
  reverses one, and a stale GST figure is worse than no figure.
* The user picks a period and a company and wants an answer now; there is no
  record to name, own or share afterwards.
* Keeping the filter and the three result tabs on one record means the figures
  on screen always belong to the filter shown above them.

Design note - where the numbers come from
-----------------------------------------
Nothing here matches on tax names. Odoo's Indian localisation (``l10n_in``,
LGPL-3) computes ``account.tax.l10n_in_gst_tax_type`` from the real repartition
tax tags (``tax_tag_igst``, ``tax_tag_cgst``, ``tax_tag_sgst``,
``tax_tag_cess``), so a tax called "GST 18%", "IGST 18" or anything else lands
in the right column as long as it is wired to the standard tags. Place of
supply is ``account.move.l10n_in_state_id``, HSN/SAC is
``account.move.line.l10n_in_hsn_code`` and the UQC is ``uom.uom.l10n_in_code``.
Amounts come from Odoo's own tax engine
(``_get_rounded_base_and_tax_lines`` plus ``_aggregate_base_lines_tax_details``),
the same code path that produces the invoice totals, so the summary and the
invoice can never disagree about rounding.

This is a check-before-you-file summary. It does not produce a return and it
does not produce a filing-ready JSON.
"""

import base64
import csv
import io
from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import frozendict

try:  # pragma: no cover - availability is environment dependent
    import xlsxwriter
except ImportError:  # pragma: no cover
    xlsxwriter = None

GST_COMPONENTS = ("cgst", "sgst", "igst", "cess")

# GSTR-1 reports unregistered recipients in their own tables. Every other
# classified outward section is a registered (B2B style) supply.
B2C_SECTIONS = (
    "sale_b2cl",
    "sale_b2cs",
    "sale_cdnur_b2cl",
)

OUTWARD_TYPES = ("out_invoice", "out_refund", "out_receipt")
INWARD_TYPES = ("in_invoice", "in_refund", "in_receipt")


class DrkdsGstSummary(models.TransientModel):
    """Filter plus results for one GST summary run."""

    _name = "drkds.gst.summary"
    _description = "GST Outward and Inward Summary"

    date_from = fields.Date(
        string="From",
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(
        string="To",
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)
    include_draft = fields.Boolean(
        string="Include Draft Documents",
        help="Off by default. A GST return is filed from posted documents; "
             "tick this only to preview what a draft batch would add.",
    )

    line_ids = fields.One2many(
        "drkds.gst.summary.line", "summary_id", string="Rate and State Lines"
    )
    outward_line_ids = fields.One2many(
        "drkds.gst.summary.line",
        "summary_id",
        string="Outward Supplies",
        domain=[("summary_type", "=", "outward")],
    )
    inward_line_ids = fields.One2many(
        "drkds.gst.summary.line",
        "summary_id",
        string="Inward Supplies",
        domain=[("summary_type", "=", "inward")],
    )
    hsn_line_ids = fields.One2many(
        "drkds.gst.hsn.line", "summary_id", string="HSN Summary"
    )

    computed = fields.Boolean(string="Computed", default=False)

    # -- reconciliation aids ------------------------------------------
    outward_taxable = fields.Monetary(string="Outward Taxable Value")
    outward_cgst = fields.Monetary(string="Outward CGST")
    outward_sgst = fields.Monetary(string="Outward SGST")
    outward_igst = fields.Monetary(string="Outward IGST")
    outward_cess = fields.Monetary(string="Outward Cess")
    outward_b2b_taxable = fields.Monetary(string="Outward B2B Taxable Value")
    outward_b2c_taxable = fields.Monetary(string="Outward B2C Taxable Value")
    inward_taxable = fields.Monetary(string="Inward Taxable Value")
    inward_cgst = fields.Monetary(string="Inward CGST")
    inward_sgst = fields.Monetary(string="Inward SGST")
    inward_igst = fields.Monetary(string="Inward IGST")
    inward_cess = fields.Monetary(string="Inward Cess")

    xlsx_file = fields.Binary(string="Export File", readonly=True, attachment=False)
    xlsx_filename = fields.Char(string="Export File Name", readonly=True)

    # -----------------------------------------------------------------
    # Gathering
    # -----------------------------------------------------------------
    @api.constrains("date_from", "date_to")
    def _check_period(self):
        for summary in self:
            if summary.date_from > summary.date_to:
                raise ValidationError("The start of the period is after its end.")

    def _move_domain(self, move_types):
        """Domain selecting the documents of one direction inside the period."""
        self.ensure_one()
        states = ["posted", "draft"] if self.include_draft else ["posted"]
        return [
            ("company_id", "=", self.company_id.id),
            ("move_type", "in", list(move_types)),
            ("state", "in", states),
            ("date", ">=", self.date_from),
            ("date", "<=", self.date_to),
        ]

    @staticmethod
    def _document_sign(move):
        """+1 for an invoice or a bill, -1 for the credit or debit note of one.

        A credit note reduces the supplies of the period it is dated in, so it
        has to be subtracted rather than listed as a separate positive figure.
        """
        return -1 if move.move_type in ("out_refund", "in_refund") else 1

    @staticmethod
    def _gst_taxes_of(base_line):
        """The distinct CGST/SGST/IGST taxes applied to one base line."""
        return {
            tax_data["tax"]
            for tax_data in base_line["tax_details"]["taxes_data"]
            if tax_data["tax"].l10n_in_gst_tax_type in ("igst", "cgst", "sgst")
        }

    @classmethod
    def _combined_rate(cls, base_line):
        """The rate a GST return would show: CGST 9 + SGST 9 becomes 18."""
        return sum(tax.amount for tax in cls._gst_taxes_of(base_line))

    @classmethod
    def _supply_type(cls, base_line):
        """Intra- or inter-state, read from the taxes actually charged."""
        types = {tax.l10n_in_gst_tax_type for tax in cls._gst_taxes_of(base_line)}
        if "igst" in types:
            return "inter"
        if types & {"cgst", "sgst"}:
            return "intra"
        return "none"

    def _collect(self, move_types):
        """Aggregate one direction into rate/state buckets and HSN buckets.

        :return: a tuple ``(rate_buckets, hsn_buckets)`` of dictionaries keyed
            by a frozen grouping key.
        """
        self.ensure_one()
        AccountTax = self.env["account.tax"]
        moves = self.env["account.move"].search(self._move_domain(move_types))
        moves = moves.filtered(lambda m: m.country_code == "IN")

        def new_bucket():
            return dict(
                {f"{c}_amount": 0.0 for c in GST_COMPONENTS},
                taxable_value=0.0,
                quantity=0.0,
                move_ids=set(),
                description=False,
            )

        rate_buckets = defaultdict(new_bucket)
        hsn_buckets = defaultdict(new_bucket)

        for move in moves:
            sign = self._document_sign(move)
            base_lines, _tax_lines = move._get_rounded_base_and_tax_lines()
            base_lines = [bl for bl in base_lines if not bl.get("special_type")]
            if not base_lines:
                continue

            def rate_key(base_line, _move=move):
                return {
                    "tax_rate": self._combined_rate(base_line),
                    "state_id": _move.l10n_in_state_id.id,
                    "supply_type": self._supply_type(base_line),
                    "gstr_section": base_line["record"].l10n_in_gstr_section or False,
                }

            def hsn_key(base_line):
                uom = base_line["product_uom_id"]
                return {
                    "hsn_code": base_line["l10n_in_hsn_code"] or "",
                    "uqc": uom.l10n_in_code or uom.name or "",
                    "tax_rate": self._combined_rate(base_line),
                }

            # Taxable value and quantity, straight from the base lines. Taking
            # these from the tax aggregation instead would double-count a line
            # carrying both CGST and SGST.
            for base_line in base_lines:
                taxable = sign * (
                    base_line["tax_details"]["total_excluded"]
                    + base_line["tax_details"]["delta_total_excluded"]
                )
                for key, bucket_map in (
                    (rate_key(base_line), rate_buckets),
                    (hsn_key(base_line), hsn_buckets),
                ):
                    bucket = bucket_map[frozendict(key)]
                    bucket["taxable_value"] += taxable
                    bucket["move_ids"].add(move.id)
                hsn_bucket = hsn_buckets[frozendict(hsn_key(base_line))]
                hsn_bucket["quantity"] += sign * base_line["quantity"]
                if not hsn_bucket["description"]:
                    product = base_line["product_id"]
                    hsn_bucket["description"] = (
                        product.name or base_line["record"].name or ""
                    )

            # Tax amounts, component by component.
            for key_builder, bucket_map in (
                (rate_key, rate_buckets),
                (hsn_key, hsn_buckets),
            ):
                def grouping_function(base_line, tax_data, _kb=key_builder):
                    if not tax_data:
                        return None
                    return {
                        **_kb(base_line),
                        "component": tax_data["tax"].l10n_in_gst_tax_type,
                    }

                aggregated = AccountTax._aggregate_base_lines_tax_details(
                    base_lines, grouping_function
                )
                per_key = AccountTax._aggregate_base_lines_aggregated_values(aggregated)
                for grouping_key, values in per_key.items():
                    if not grouping_key or not grouping_key["component"]:
                        continue
                    component = grouping_key["component"]
                    bucket_key = {
                        k: v for k, v in grouping_key.items() if k != "component"
                    }
                    bucket = bucket_map[frozendict(bucket_key)]
                    bucket[f"{component}_amount"] += sign * values["tax_amount"]

        return rate_buckets, hsn_buckets

    # -----------------------------------------------------------------
    # Actions
    # -----------------------------------------------------------------
    def action_compute(self):
        """Build the three views and stay on the same screen."""
        self.ensure_one()
        self._check_period()
        self.line_ids.unlink()
        self.hsn_line_ids.unlink()
        currency = self.company_id.currency_id

        rate_vals, hsn_vals = [], []
        totals = {}
        for direction, move_types in (
            ("outward", OUTWARD_TYPES),
            ("inward", INWARD_TYPES),
        ):
            rate_buckets, hsn_buckets = self._collect(move_types)
            totals[direction] = defaultdict(float)
            for key, bucket in rate_buckets.items():
                taxes = {c: bucket[f"{c}_amount"] for c in GST_COMPONENTS}
                total_tax = sum(taxes.values())
                if currency.is_zero(bucket["taxable_value"]) and currency.is_zero(total_tax):
                    continue
                rate_vals.append({
                    "summary_id": self.id,
                    "summary_type": direction,
                    "currency_id": currency.id,
                    "taxable_value": bucket["taxable_value"],
                    "total_tax": total_tax,
                    "invoice_total": bucket["taxable_value"] + total_tax,
                    "move_count": len(bucket["move_ids"]),
                    "move_ids": [(6, 0, sorted(bucket["move_ids"]))],
                    **{f"{c}_amount": taxes[c] for c in GST_COMPONENTS},
                    **key,
                })
                totals[direction]["taxable"] += bucket["taxable_value"]
                for component in GST_COMPONENTS:
                    totals[direction][component] += taxes[component]
            for key, bucket in hsn_buckets.items():
                taxes = {c: bucket[f"{c}_amount"] for c in GST_COMPONENTS}
                total_tax = sum(taxes.values())
                if currency.is_zero(bucket["taxable_value"]) and currency.is_zero(total_tax):
                    continue
                hsn_vals.append({
                    "summary_id": self.id,
                    "summary_type": direction,
                    "currency_id": currency.id,
                    "description": bucket["description"] or "",
                    "quantity": bucket["quantity"],
                    "taxable_value": bucket["taxable_value"],
                    "total_tax": total_tax,
                    "move_ids": [(6, 0, sorted(bucket["move_ids"]))],
                    **{f"{c}_amount": taxes[c] for c in GST_COMPONENTS},
                    **key,
                })

        self.env["drkds.gst.summary.line"].create(rate_vals)
        self.env["drkds.gst.hsn.line"].create(hsn_vals)

        self.update({
            "computed": True,
            "xlsx_file": False,
            "xlsx_filename": False,
            "outward_taxable": totals["outward"]["taxable"],
            "outward_cgst": totals["outward"]["cgst"],
            "outward_sgst": totals["outward"]["sgst"],
            "outward_igst": totals["outward"]["igst"],
            "outward_cess": totals["outward"]["cess"],
            "inward_taxable": totals["inward"]["taxable"],
            "inward_cgst": totals["inward"]["cgst"],
            "inward_sgst": totals["inward"]["sgst"],
            "inward_igst": totals["inward"]["igst"],
            "inward_cess": totals["inward"]["cess"],
        })
        self._compute_registration_split()
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": self.env.context,
        }

    def _compute_registration_split(self):
        """Split outward taxable value into B2B and B2C.

        The split is read from ``account.move.line.l10n_in_gstr_section``, which
        the Indian localisation sets from the tax tags and the GST treatment of
        the document when it is saved. That is the same classification a return
        would use, so it is used here rather than a guess at the recipient's
        registration status. Lines the localisation left unclassified are
        reported separately instead of being pushed into one side.
        """
        self.ensure_one()
        b2b = b2c = 0.0
        for line in self.outward_line_ids:
            section = line.gstr_section or ""
            if section in B2C_SECTIONS:
                b2c += line.taxable_value
            elif section:
                b2b += line.taxable_value
        self.outward_b2b_taxable = b2b
        self.outward_b2c_taxable = b2c

    def action_open_outward_moves(self):
        """All outward documents of the period, for a quick eyeball."""
        return self._action_open_moves(OUTWARD_TYPES, "Outward Documents")

    def action_open_inward_moves(self):
        """All inward documents of the period."""
        return self._action_open_moves(INWARD_TYPES, "Inward Documents")

    def _action_open_moves(self, move_types, name):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": self._move_domain(move_types),
            "context": {"create": False},
        }

    # -----------------------------------------------------------------
    # Export
    # -----------------------------------------------------------------
    def action_export(self):
        """Export the three views as XLSX when possible, CSV otherwise.

        ``xlsxwriter`` ships with Odoo, but a slim install can be missing it,
        so the CSV path is a real fallback rather than dead code. No new pip
        dependency is introduced either way.
        """
        self.ensure_one()
        if not self.computed:
            raise UserError("Compute the summary before exporting it.")
        if xlsxwriter:
            data, name = self._build_xlsx(), "gst_summary_%s_%s.xlsx" % (
                self.date_from, self.date_to)
        else:
            data, name = self._build_csv(), "gst_summary_%s_%s.csv" % (
                self.date_from, self.date_to)
        self.write({"xlsx_file": data, "xlsx_filename": name})
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content?model=%s&id=%s&field=xlsx_file"
                   "&filename_field=xlsx_filename&download=true" % (self._name, self.id),
            "target": "self",
        }

    def _export_tables(self):
        """The three tables as ``(sheet name, headers, rows)`` triples."""
        self.ensure_one()
        rate_headers = [
            "Rate (%)", "Place of Supply", "Supply Type", "Taxable Value",
            "CGST", "SGST", "IGST", "Cess", "Total Tax", "Documents",
        ]

        def rate_rows(direction):
            return [
                [
                    line.tax_rate,
                    line.state_id.name or "",
                    dict(line._fields["supply_type"].selection).get(line.supply_type, ""),
                    line.taxable_value, line.cgst_amount, line.sgst_amount,
                    line.igst_amount, line.cess_amount, line.total_tax, line.move_count,
                ]
                for line in self.line_ids.filtered(
                    lambda l: l.summary_type == direction)
            ]

        hsn_rows = [
            [
                line.hsn_code, line.description or "", line.uqc or "", line.quantity,
                line.tax_rate, line.taxable_value, line.cgst_amount, line.sgst_amount,
                line.igst_amount, line.cess_amount, line.total_tax,
                dict(line._fields["summary_type"].selection)[line.summary_type],
            ]
            for line in self.hsn_line_ids
        ]
        return [
            ("Outward", rate_headers, rate_rows("outward")),
            ("Inward", rate_headers, rate_rows("inward")),
            ("HSN Summary", [
                "HSN/SAC", "Description", "UQC", "Quantity", "Rate (%)",
                "Taxable Value", "CGST", "SGST", "IGST", "Cess", "Total Tax",
                "Direction",
            ], hsn_rows),
        ]

    def _build_xlsx(self):
        """Render the three tables into a base64 XLSX workbook."""
        self.ensure_one()
        stream = io.BytesIO()
        workbook = xlsxwriter.Workbook(stream, {"in_memory": True})
        bold = workbook.add_format({"bold": True})
        money = workbook.add_format({"num_format": "#,##0.00"})
        for sheet_name, headers, rows in self._export_tables():
            sheet = workbook.add_worksheet(sheet_name)
            sheet.write_row(0, 0, headers, bold)
            for row_index, row in enumerate(rows, start=1):
                for col_index, value in enumerate(row):
                    if isinstance(value, float):
                        sheet.write_number(row_index, col_index, value, money)
                    elif isinstance(value, int):
                        sheet.write_number(row_index, col_index, value)
                    else:
                        sheet.write_string(row_index, col_index, str(value))
            sheet.set_column(0, len(headers) - 1, 16)
        workbook.close()
        return base64.b64encode(stream.getvalue())

    def _build_csv(self):
        """Render the three tables into one base64 CSV, table after table."""
        self.ensure_one()
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        for sheet_name, headers, rows in self._export_tables():
            writer.writerow([sheet_name])
            writer.writerow(headers)
            writer.writerows(rows)
            writer.writerow([])
        return base64.b64encode(buffer.getvalue().encode("utf-8"))
