{
    "name": "Mass Update",
    "summary": "Update one field on many selected records from the list view, as the current user, with a clear report of what could not be changed",
    "description": """
Mass Update
===========

Select records in any list, pick a field, give it a value, apply. Every
selected record is written in one go, as you, with your own access rights.
Records you are not allowed to change are reported by name, not silently
skipped and not turned into a crash that undoes the rest.

What it does
------------
* **Settings > Technical > Mass Update** - the administrator lists the models
  on which mass update is allowed. Enabling a model adds a *Mass update*
  entry to the Actions menu of its list view; disabling removes it again.
  The wizard refuses any model that is not enabled.
* **The wizard** - shows how many records are selected, offers only the fields
  that can actually be written (stored, writable, not an identifier, not a
  timestamp, not a binary, not a computed field without an inverse) in a
  picker you search by typing part of the field's name, and a value input
  matching the field type: text, number, yes/no, date, date and time,
  selection, record, tag.
* **Set empty** - clears the field on every selected record instead of
  setting a value (not offered on a required field).
* **Batches of 500, never as superuser** - the write runs as the current user
  in batches of 500. When a batch is refused by an access rule, each record
  of that batch is retried alone, so one locked record never blocks the
  other 499.
* **A result you can act on** - updated count, failed count, and the list of
  records that could not be changed with the reason.
* **Private wizard** - each wizard, with the fields and choices it offers,
  is visible to the user who opened it only, so nobody else can change what
  it is about to write.

Who can use it
--------------
The administrator (Settings group) decides which models are enabled. Any
internal user with write access on an enabled model can run the wizard; the
model's own access rights and record rules decide what each user may change.
Restrictions that exist only in a form view (a field read-only in some
state) are not applied, so enable only models where that is acceptable.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Extra Tools",
    "author": "drkds",
    "website": "https://drkdsinfo.com",
    "support": "jyotin@drkdsinfo.com",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "security/drkds_mass_update_security.xml",
        "wizard/drkds_mass_update_wizard_views.xml",
        "views/drkds_mass_update_model_views.xml",
    ],
    "images": [
        "static/description/screenshot_01.png",
        "static/description/screenshot_02.png",
        "static/description/screenshot_03.png",
        "static/description/screenshot_04.png",
        "static/description/screenshot_05.png",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "uninstall_hook": "uninstall_hook",
}
