from odoo import fields, models

#: Wording most Indian SMEs print under the line table. Editable because the
#: exact sentence is a matter of house style, not of statute.
DEFAULT_DECLARATION = (
    "We declare that this invoice shows the actual price of the goods "
    "described and that all particulars are true and correct."
)


class ResCompany(models.Model):
    """Holds the declaration text printed on the Indian invoice PDF."""

    _inherit = "res.company"

    drkds_in_invoice_declaration = fields.Text(
        string="Invoice Declaration",
        default=DEFAULT_DECLARATION,
        help="Declaration printed in the footer of the Indian invoice PDF. "
        "Clear this field to print no declaration at all.",
    )
