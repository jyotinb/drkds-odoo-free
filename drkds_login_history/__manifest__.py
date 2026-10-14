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
One row per event, with the result **Success**, **2FA Pending**, **Failed**
or **Logout**:

* the user (when the login name matched one, archived users included) and
  the login name as typed,
* the date and time,
* the IP address the request came from,
* the raw user agent, plus the browser and operating system read from it by
  a small parser of our own (no external library, no outbound call),
* a SHA-256 hash of the session cookie, never the cookie itself.

Values sent by the client are cut to a fixed length: login 255, user agent
1024 and address 64 characters.

No geolocation is attempted, so the Country column stays empty by design:
this module makes no network call to anybody.

How it is recorded
------------------
The success and failure paths of ``res.users._login`` and the
``/web/session/logout`` and ``/web/session/destroy`` routes are hooked, so
the browser form, JSON-RPC, XML-RPC and passkey logins are all recorded. A
failed login makes Odoo roll back the request, so each row is written through
its own database cursor and committed on the spot. If the table cannot be
written (for example while the module is being uninstalled) the event is
logged to the server log and the login itself is never blocked.

With two-factor authentication a right password is recorded as **2FA
Pending**, because the user is not signed in yet; the code step then writes
its own **Success** or **Failed** row. A browser remembered by 2FA skips the
code, so its login is a plain **Success**.

An integration's ``authenticate`` call is a login and gets a row. The
API-key calls it makes afterwards are not logins and are not recorded, so the
table does not grow with every request. Odoo hides the HTTP request from its
XML-RPC services, so XML-RPC rows carry no address or browser.

Where to look
-------------
Settings, Users & Companies, Login History: a list with Today, Failed,
Success and 2FA Pending filters (days in your timezone), grouping by user and
by day, and a graph of events per day.
Every user form carries two buttons: Last Login (the last successful login,
opening that user's rows) and Failed Today (the failed attempts of today,
opening those attempts).

Housekeeping
------------
A daily scheduled action deletes rows older than the number of days set in
Settings, General Settings, Login History (default 180; 0 keeps everything).

Who can see it
--------------
The menu, the action, the model and the two figures on the user form are
restricted to Settings administrators (``base.group_system``). Rows cannot
be created or edited from the interface.

Part of the drkds Indian SME suite for Odoo 19 Community.
""",
    "version": "19.0.1.0.0",
    "category": "Extra Tools",
    "author": "drkds",
    "website": "https://drkdsinfo.com",
    "support": "jyotin@drkdsinfo.com",
    "license": "LGPL-3",
    "depends": ["base", "web", "base_setup"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/drkds_login_record_views.xml",
        "views/res_users_views.xml",
        "views/res_config_settings_views.xml",
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
}
