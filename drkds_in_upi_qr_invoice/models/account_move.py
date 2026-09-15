"""UPI payment deep link and QR code for customer invoices.

The link follows the NPCI *UPI Linking Specifications* (common URL
specifications for deep linking, version 1.6 / 1.7), which define a payment
intent as ``upi://pay?<param>=<value>&...``. The parameters used here are:

``pa``
    Payee address. The Virtual Payment Address the money goes to, written
    ``name@handle``. Mandatory.
``pn``
    Payee name, displayed by the payer's UPI application before it asks for
    the PIN. Mandatory.
``am``
    Transaction amount, in the currency given by ``cu``. Optional: when it is
    absent the payer types the amount in. Written with two decimals.
``cu``
    Currency code. The specification only supports ``INR`` today.
``tn``
    Transaction note, a short free-text description shown to the payer and
    carried into their passbook. Optional.
``tr``
    Transaction reference, the merchant's own reference for the collection.
    Optional, but it is what lets an incoming credit be matched back to an
    invoice. Optional.

Every value is percent-encoded, because a payee name or an invoice reference
may legitimately contain spaces, ampersands or slashes, and an unencoded one
truncates the link at the reader.

Odoo's own QR rendering is reused: ``ir.actions.report.barcode`` with a
``QR`` barcode type, the same reportlab-backed helper that serves the
``/report/barcode/QR/...`` controller.
"""

import base64
from urllib.parse import quote, urlencode

from odoo import api, fields, models
from odoo.tools.image import image_data_uri

#: NPCI supports no other currency in a payment intent.
UPI_CURRENCY = "INR"

#: Pixel size of the rendered QR code. Large enough that the 180 dpi PDF
#: rasterisation stays scannable from a phone held at arm's length.
UPI_QR_SIZE = 180


class AccountMove(models.Model):
    _inherit = "account.move"

    drkds_upi_qr_available = fields.Boolean(
        string="UPI QR Available",
        compute="_compute_drkds_upi_qr_available",
        help="Technical flag. True when a UPI QR code should be printed on "
        "this document.",
    )

    @api.depends(
        "move_type", "state", "amount_residual", "currency_id",
        "company_id.drkds_upi_vpa", "company_id.drkds_upi_include_amount",
    )
    def _compute_drkds_upi_qr_available(self):
        for move in self:
            move.drkds_upi_qr_available = move._drkds_upi_is_collectible()

    # ------------------------------------------------------------------
    # Eligibility
    # ------------------------------------------------------------------
    def _drkds_upi_is_collectible(self):
        """Tell whether this document may carry a UPI collection QR code.

        A QR code is an instruction to pay us, so it is printed only where
        that instruction is true:

        * customer invoices only. Never a vendor bill, where the money moves
          the other way, and never a credit note, where we owe the customer.
        * posted only. A draft invoice is not a demand for money yet.
        * something must still be due. A fully paid invoice gets no QR code.
        * the company must have a UPI ID configured.
        * when the amount is embedded the invoice must be in INR, because
          that is the only currency a UPI intent can carry.
        """
        self.ensure_one()
        company = self.company_id
        if self.move_type != "out_invoice" or self.state != "posted":
            return False
        if not company.drkds_upi_vpa:
            return False
        if self.currency_id.compare_amounts(self.amount_residual, 0) <= 0:
            return False
        if company.drkds_upi_include_amount and self.currency_id.name != UPI_CURRENCY:
            return False
        # Odoo's Indian localisation prints its own UPI QR code on the
        # invoice. Stand aside rather than print a second one.
        if company._fields.get("l10n_in_upi_id") and company.l10n_in_upi_id:
            return False
        return True

    # ------------------------------------------------------------------
    # Deep link
    # ------------------------------------------------------------------
    def _drkds_upi_payment_url(self):
        """Return the ``upi://pay`` deep link for this invoice, or False."""
        self.ensure_one()
        if not self._drkds_upi_is_collectible():
            return False
        company = self.company_id
        params = [
            ("pa", company.drkds_upi_vpa),
            ("pn", company.drkds_upi_payee_name or company.name),
        ]
        if company.drkds_upi_include_amount:
            params.append(("am", "%.2f" % self.amount_residual))
        params.append(("cu", UPI_CURRENCY))
        if company.drkds_upi_include_reference:
            reference = self.payment_reference or self.name
            params.append(("tn", "Invoice %s" % reference))
            params.append(("tr", reference))
        # quote_via=quote keeps a space as %20 rather than "+", which some
        # UPI applications show verbatim in the transaction note.
        return "upi://pay?" + urlencode(params, quote_via=quote)

    # ------------------------------------------------------------------
    # QR image
    # ------------------------------------------------------------------
    def _drkds_upi_qr_data_uri(self):
        """Return the QR code as a data URI an ``<img src>`` can use.

        Rendering goes through ``ir.actions.report.barcode``, Odoo's own
        barcode helper, so no extra library and no extra dependency.
        """
        self.ensure_one()
        url = self._drkds_upi_payment_url()
        if not url:
            return False
        barcode = self.env["ir.actions.report"].barcode(
            barcode_type="QR",
            value=url,
            width=UPI_QR_SIZE,
            height=UPI_QR_SIZE,
            quiet=0,
            barLevel="M",
        )
        return image_data_uri(base64.b64encode(barcode))
