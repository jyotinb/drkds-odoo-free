# Part of the drkds free suite for Odoo 19 Community. See LICENSE (LGPL-3).
"""Record the logout before the session is cleared.

Core ends a session through two routes: ``/web/session/logout`` (the user
menu, a plain HTTP redirect) and ``/web/session/destroy`` (JSON-RPC, used by
external and mobile clients). Both wipe ``request.session``, so the user id
and login are read before ``super()`` runs. The routes keep core's read-only
declaration: the row is written through the detached writer's own read/write
cursor, never through the request's cursor.
"""

from odoo import http
from odoo.addons.web.controllers.session import Session
from odoo.http import request


class DrkdsLoginHistorySession(Session):
    @staticmethod
    def _drkds_log_logout():
        uid = request.session.uid
        if uid and "drkds.login.record" in request.env.registry:
            request.env["drkds.login.record"]._drkds_log_event(
                "logout", login=request.session.login, uid=uid
            )

    @http.route()
    def logout(self, redirect="/odoo"):
        self._drkds_log_logout()
        return super().logout(redirect=redirect)

    @http.route()
    def destroy(self):
        self._drkds_log_logout()
        return super().destroy()
