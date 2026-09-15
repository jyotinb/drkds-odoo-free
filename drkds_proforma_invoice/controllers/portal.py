from odoo import SUPERUSER_ID, _, http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal


class DrkdsProformaPortal(CustomerPortal):
    """Portal access to proforma invoices.

    Access is never decided here. A proforma is visible on the portal only if
    the sale order it was drawn from is, and that question is answered by
    Odoo's own ``_document_check_access`` on ``sale.order``. A proforma with no
    sale order behind it - one drawn from a draft invoice, for instance - is
    simply not reachable from the portal.
    """

    def _drkds_proforma_check_access(self, proforma_id, access_token=None):
        proforma_sudo = request.env["drkds.proforma.invoice"].with_user(
            SUPERUSER_ID
        ).browse(proforma_id).exists()
        if not proforma_sudo:
            raise MissingError(_("This proforma invoice does not exist."))
        order = proforma_sudo._portal_source_order()
        if not order:
            raise AccessError(_(
                "This proforma invoice is not published on the portal."
            ))
        # Delegates entirely to the sale order's portal access rules.
        self._document_check_access("sale.order", order.id, access_token=access_token)
        return proforma_sudo

    @http.route(
        ["/my/proforma/<int:proforma_id>"],
        type="http", auth="public", website=True,
    )
    def drkds_portal_proforma(
        self, proforma_id, access_token=None, report_type=None, download=False, **kw
    ):
        try:
            proforma_sudo = self._drkds_proforma_check_access(
                proforma_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        if report_type in ("html", "pdf", "text"):
            return self._show_report(
                model=proforma_sudo,
                report_type=report_type,
                report_ref="drkds_proforma_invoice.action_report_drkds_proforma_invoice",
                download=download,
            )

        values = {
            "proforma": proforma_sudo,
            "doc": proforma_sudo,
            "token": access_token,
            "page_name": "proforma_invoice",
            "report_type": "html",
        }
        return request.render(
            "drkds_proforma_invoice.portal_drkds_proforma_page", values
        )
