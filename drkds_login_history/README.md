# Login History

Who signed in, from where, and which attempts failed: a login audit trail
for Odoo 19 Community.

## Why

Odoo Community already keeps the devices behind a user's *successful*
sessions (Settings > Users & Companies > Devices). It does not keep the
attempts that failed, the login name that was typed, or the moment a session
was ended. This module records all three in one table that a Settings
administrator can read, filter and chart.

## What is recorded

One row per event with the result **Success**, **Failed** or **Logout**:

| Field | Content |
| --- | --- |
| User | The user whose login name matched. Empty for an unknown login name. |
| Login Typed | The login name exactly as typed, right or wrong. |
| Date | Date and time of the event (UTC in the database, your timezone on screen). |
| IP Address | The address the request came from (proxy mode is honoured). |
| User Agent | The raw browser string. |
| Browser, Operating System | Read from the user agent by a small parser of our own. No external library. |
| Session Hash | SHA-256 of the session identifier. The identifier itself is never stored. |
| Country | Always empty. No geolocation lookup is made because this module makes no outbound network call. |

## How it is recorded

- The success and failure paths of `res.users._login` are hooked, so every
  interactive, RPC and passkey login passes through it.
- The `/web/session/logout` route is extended to write the logout row before
  the session is cleared.
- A failed login makes Odoo roll back the request. Each row is therefore
  written through its own database cursor and committed at once, so the
  failed attempt survives.
- The writer never blocks a login. If the table cannot be written (for
  example while the module is being uninstalled on a running server) the
  event goes to the server log and authentication proceeds unchanged.

## Where to find it

- **Settings > Users & Companies > Login History**: list, graph (events per
  day, stacked by result) and a read-only form. Filters: Today, Last 7 Days,
  Failed, Success, Logout, Unknown Login Name. Group by user, result, day or
  IP address.
- **User form** (Settings > Users & Companies > Users): a Login History
  button showing the failed attempts of today and the last successful login,
  opening that user's rows.

## Configure

Settings > General Settings > Login History > **Keep Login History (days)**,
default 180. A daily scheduled action, *Login History: purge old records*,
deletes rows older than that. Set 0 to keep every row forever.

## Access

The menu, the action and the model are restricted to Settings administrators
(`base.group_system`). Rows cannot be created or edited from the interface;
administrators may delete them.

## Install

Copy the folder into your addons path, update the apps list and install
**Login History**. Depends on `base`, `web` and `base_setup` (the General
Settings page). Odoo 19 Community, LGPL-3. Recording starts at the next login
after installation; nothing is back-filled.

## Notes

- A hash of the session identifier is kept only to tell events of one session
  apart. Odoo rotates the identifier when a login succeeds, so the success and
  logout rows of one visit carry different hashes.
- The failed attempts of today are counted in the timezone of the user
  looking at the form.
- No data leaves your server. There is no telemetry and no geolocation.

Part of the drkds Indian SME suite for Odoo 19 Community.
