{
    "name": "Login History",
    "summary": "Who signed in, from where, and when it failed: a login audit trail",
    "description": """
Login History
=============

Odoo Community already lists the devices behind a user's *successful*
sessions (Settings, Users, Devices). It does not keep the attempts that
failed, the login name somebody typed, or the moment a session was ended.
This module records all of that in one table an administrator can read.

What is recorded
----------------
One row per event, with the result **Success**, **Failed** or **Logout**:

* the user (when the login name matched one) and the login name as typed,
* the date and time,
* the IP address the request came from,
* the raw user agent, plus the browser and operating system read from it by
  a small parser of our own (no external library, no outbound call),
* a SHA-256 hash of the session cookie, never the cookie itself.

No geolocation is attempted, so the Country column stays empty by design:
this module makes no network call to anybody.

How it is recorded
------------------
The success and failure paths of ``res.users._login`` and the
``/web/session/logout`` route are hooked. A failed login makes Odoo roll back
the request, so each row is written through its own database cursor and
committed on the spot. If the table cannot be written (for example while the
module is being uninstalled) the event is logged to the server log and the
login itself is never blocked.

Where to look
-------------
Settings, Users & Companies, Login History: a list with Today, Failed and
Success filters, grouping by user and by day, and a graph of events per day.
Every user form carries a Login History button showing the last successful
login and the failed attempts of today.

Housekeeping
------------
A daily scheduled action deletes rows older than the number of days set in
Settings, General Settings, Login History (default 180; 0 keeps everything).

Who can see it
--------------
The menu, the action and the model are restricted to Settings
administrators (``base.group_system``). Rows cannot be created or edited
from the interface.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Extra Tools",
    "author": "drkds",
    "website": "https://drkdsinfo.com",
    "support": "jyotinboghani@gmail.com",
    "license": "LGPL-3",
    "depends": ["base", "web", "base_setup"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/drkds_login_record_views.xml",
        "views/res_users_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
}
