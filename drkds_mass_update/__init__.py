# Part of the drkds free suite for Odoo 19 Community. See LICENSE (LGPL-3).
from . import models
from . import wizard
from .models.drkds_mass_update_model import WIZARD_MODEL


def uninstall_hook(env):
    """Remove every bound server action that opens the wizard.

    The actions are created by code when a model is enabled, not by a data
    file, so Odoo's data cleanup does not know about them. Left behind, each
    one would still appear in a list view's Actions menu and fail on click
    because the wizard it opens is gone. Besides the actions the enabled
    lines own (renamed or edited ones included), this removes any server
    action whose code still opens the wizard, such as a duplicate made from
    the server action form, which no line knows about.
    """
    env["drkds.mass.update.model"].search([])._drkds_remove_server_action()
    env["ir.actions.server"].search(
        [("state", "=", "code"), ("code", "like", WIZARD_MODEL)]
    ).unlink()
