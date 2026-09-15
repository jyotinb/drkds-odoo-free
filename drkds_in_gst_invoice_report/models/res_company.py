from odoo import fields, models

#: Wording most Indian SMEs print under the line table. Kept editable because
#: the exact sentence is a matter of house style, not of statute.
DEFAULT_DECLARATION = (
    "We declare that this invoice shows the actual price of the goods "
    "described and that all particulars are true and correct."
)


class ResCompany(models.Model):
    """Carries the per-company text blocks printed on the GST tax invoice."""

    _inherit = "res.company"

    drkds_in_invoice_declaration = fields.Text(
        string="GST Invoice Declaration",
        default=DEFAULT_DECLARATION,
        help="Declaration printed in the footer of the GST tax invoice. "
        "Leave empty to print no declaration at all.",
    )
