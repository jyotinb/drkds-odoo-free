# Part of the drkds free suite for Odoo 19 Community. See LICENSE (LGPL-3).
"""Record the logout before the session is cleared.

``/web/session/logout`` wipes ``request.session``, so the user id and login
have to be read before ``super()`` runs. The route keeps core's read-only
declaration: the row is written through the detached writer's own
read/write cursor, never through the request's cursor.
"""

from odoo import http
from odoo.addons.web.controllers.session import Session
from odoo.http import request


class DrkdsLoginHistorySession(Session):
    @http.route()
    def logout(self, redirect="/odoo"):
        uid = request.session.uid
        if uid and "drkds.login.record" in request.env.registry:
            request.env["drkds.login.record"]._drkds_log_event(
                "logout", login=request.session.login, uid=uid
            )
        return super().logout(redirect=redirect)
