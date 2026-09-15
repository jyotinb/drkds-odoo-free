"""Result rows produced by a GST summary run.

Both models are transient. A summary is a view of the ledger at a moment in
time; storing it would create a second source of truth that silently goes
stale the next time somebody posts a back-dated invoice. Every row keeps the
set of moves it was built from, so a figure can always be opened and read back
to the invoices that produced it.
"""

from odoo import fields, models


class DrkdsGstSummaryLine(models.TransientModel):
    """One (rate, place of supply) bucket of a GST summary.

    The rate is the combined GST rate of the invoice line: for an intra-state
    supply CGST 9% + SGST 9% is reported as a single 18% bucket, which is how
    both GSTR-1 and GSTR-3B present it.
    """

    _name = "drkds.gst.summary.line"
    _description = "GST Summary Line by Rate and Place of Supply"
    _order = "summary_type, supply_type, tax_rate, id"

    summary_id = fields.Many2one(
        "drkds.gst.summary",
        string="Summary",
        required=True,
        ondelete="cascade",
        index=True,
    )
    summary_type = fields.Selection(
        [("outward", "Outward"), ("inward", "Inward")],
        string="Direction",
        required=True,
    )
    tax_rate = fields.Float(string="GST Rate (%)", digits=(5, 2))
    state_id = fields.Many2one("res.country.state", string="Place of Supply")
    supply_type = fields.Selection(
        [("intra", "Intra-state"), ("inter", "Inter-state"), ("none", "No GST")],
        string="Supply Type",
    )
    gstr_section = fields.Selection(
        selection=lambda self: self.env["account.move.line"]._fields["l10n_in_gstr_section"].selection,
        string="GSTR Section",
        help="The section the Indian localisation itself assigned to the invoice "
             "lines in this bucket, such as B2B Regular or B2CS. It is the table "
             "the supply would be reported under.",
    )
    taxable_value = fields.Monetary(string="Taxable Value")
    cgst_amount = fields.Monetary(string="CGST")
    sgst_amount = fields.Monetary(string="SGST")
    igst_amount = fields.Monetary(string="IGST")
    cess_amount = fields.Monetary(string="Cess")
    total_tax = fields.Monetary(string="Total Tax")
    invoice_total = fields.Monetary(string="Taxable + Tax")
    move_count = fields.Integer(string="Documents")
    move_ids = fields.Many2many("account.move", string="Source Documents")
    currency_id = fields.Many2one("res.currency", string="Currency")

    def action_open_moves(self):
        """Drill down from a summary figure to the journal entries behind it."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Documents in this bucket",
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", self.move_ids.ids)],
            "context": {"create": False},
        }


class DrkdsGstHsnLine(models.TransientModel):
    """One (HSN/SAC, UQC, rate) bucket of the HSN summary.

    Mirrors the HSN table of GSTR-1: quantity and taxable value are summed per
    code, and the tax is split by component so that a rate can be checked
    against the value it was charged on.
    """

    _name = "drkds.gst.hsn.line"
    _description = "GST HSN/SAC Summary Line"
    _order = "summary_type, hsn_code, tax_rate, id"

    summary_id = fields.Many2one(
        "drkds.gst.summary",
        string="Summary",
        required=True,
        ondelete="cascade",
        index=True,
    )
    summary_type = fields.Selection(
        [("outward", "Outward"), ("inward", "Inward")],
        string="Direction",
        required=True,
    )
    hsn_code = fields.Char(string="HSN/SAC")
    description = fields.Char(string="Description")
    uqc = fields.Char(
        string="UQC",
        help="Unique Quantity Code. Taken from the GST UQC set on the unit of "
             "measure when there is one, otherwise the unit of measure name.",
    )
    quantity = fields.Float(string="Quantity", digits="Product Unit of Measure")
    tax_rate = fields.Float(string="GST Rate (%)", digits=(5, 2))
    taxable_value = fields.Monetary(string="Taxable Value")
    cgst_amount = fields.Monetary(string="CGST")
    sgst_amount = fields.Monetary(string="SGST")
    igst_amount = fields.Monetary(string="IGST")
    cess_amount = fields.Monetary(string="Cess")
    total_tax = fields.Monetary(string="Total Tax")
    move_ids = fields.Many2many("account.move", string="Source Documents")
    currency_id = fields.Many2one("res.currency", string="Currency")

    def action_open_moves(self):
        """Drill down from an HSN row to the journal entries behind it."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Documents for this HSN/SAC",
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", self.move_ids.ids)],
            "context": {"create": False},
        }
