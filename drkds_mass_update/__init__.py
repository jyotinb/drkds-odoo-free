# Part of the drkds free suite for Odoo 19 Community. See LICENSE (LGPL-3).
from . import models
from . import wizard


def uninstall_hook(env):
    """Remove every bound server action this module created.

    The actions are created by code when a model is enabled, not by a data
    file, so Odoo's data cleanup does not know about them. Left behind, each
    one would still appear in a list view's Actions menu and fail on click
    because the wizard it opens is gone.
    """
    env["drkds.mass.update.model"].search([])._drkds_remove_server_action()
