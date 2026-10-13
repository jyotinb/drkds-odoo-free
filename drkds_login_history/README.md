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

One row per event with the result **Success**, **2FA Pending**, **Failed**
or **Logout**:

| Field | Content |
| --- | --- |
| User | The user whose login name matched, archived users included. Empty for an unknown login name. |
| Login Typed | The login name exactly as typed, right or wrong (first 255 characters). |
| Date | Date and time of the event (UTC in the database, your timezone on screen). |
| IP Address | The address the request came from (proxy mode is honoured). Empty for XML-RPC logins. |
| User Agent | The raw browser string (first 1024 characters). |
| Browser, Operating System | Read from the user agent by a small parser of our own. No external library. |
| Session Hash | SHA-256 of the session identifier. The identifier itself is never stored. |
| Country | Always empty. No geolocation lookup is made because this module makes no outbound network call. |

## How it is recorded

- The success and failure paths of `res.users._login` are hooked, so every
  interactive, RPC and passkey login passes through it: the browser form,
  `/web/session/authenticate` (JSON-RPC) and `/xmlrpc/2/common`
  `authenticate`/`login`.
- The `/web/session/logout` route (user menu) and the `/web/session/destroy`
  route (JSON-RPC clients) are extended to write the logout row before the
  session is cleared.
- **Two-factor authentication.** A right password for a user with 2FA does
  not sign the user in yet, so it is recorded as **2FA Pending**. The code
  step writes its own row: **Success** for a right code, **Failed** for a
  wrong or reused code or too many tries. A browser remembered by 2FA skips
  the code, so that login is a plain **Success**. A stolen password stopped
  by 2FA therefore shows as 2FA Pending followed by Failed, or by nothing.
- **API keys.** An integration's `authenticate` call is a login and gets a
  row, whether it presents a password or an API key. The calls it then makes
  with the key (`/xmlrpc/2/object`, `/json/2/...`) are not logins and are not
  recorded, so an integration cannot fill the table with one row per request.
  A wrong key on those calls is refused by Odoo and not recorded either.
- A failed login makes Odoo roll back the request. Each row is therefore
  written through its own database cursor and committed at once, so the
  failed attempt survives.
- The writer never blocks a login. If the table cannot be written (for
  example while the module is being uninstalled on a running server) the
  event goes to the server log and authentication proceeds unchanged.

## Where to find it

- **Settings > Users & Companies > Login History**: list, graph (events per
  day, stacked by result) and a read-only form. Filters: Today, Last 7 Days
  (both by day in your timezone), Failed, Success, 2FA Pending, Logout,
  Unknown Login Name. Group by user, result, day or IP address.
- **User form** (Settings > Users & Companies > Users): a Login History
  button showing the failed attempts of today and the last successful login,
  opening that user's rows.

## Configure

Settings > General Settings > Login History > **Keep Login History (days)**,
default 180. A daily scheduled action, *Login History: purge old records*,
deletes rows older than that. Set 0 to keep every row forever.

## Access

The menu, the action, the model and the two figures on the user form are
restricted to Settings administrators (`base.group_system`). Rows cannot be
created or edited from the interface or over RPC; administrators may delete
them.

## Install

Copy the folder into your addons path, update the apps list and install
**Login History**. Depends on `base`, `web` and `base_setup` (the General
Settings page). Odoo 19 Community, LGPL-3. Recording starts at the next login
after installation; nothing is back-filled.

## Notes

- A hash of the session identifier is kept only to tell events of one session
  apart. Odoo rotates the identifier when a login succeeds, so the success and
  logout rows of one visit carry different hashes. The 2FA Pending row and the
  code step that follows it share one hash.
- The login name is matched exactly as Odoo matches it: `ADMIN` or ` admin `
  is not the user `admin`, so such an attempt is listed with an empty User.
- Odoo's own cooldown (`base.login_cooldown_after`, default 5 failures, then
  `base.login_cooldown_duration` seconds) refuses further attempts from that
  address without checking them. Each refused attempt is still recorded as
  Failed.
- Odoo hides the HTTP request from its XML-RPC services (its own log line
  reads "from n/a"), so XML-RPC logins carry no IP address, browser or session
  hash. The JSON-RPC route `/web/session/authenticate` carries all of them.
- Behind a reverse proxy, Odoo takes the address from `X-Forwarded-For` only
  when proxy mode is on and the proxy also sends `X-Forwarded-Host`. With
  proxy mode off the header is ignored and cannot be spoofed. Turn proxy mode
  on only when Odoo is reachable through the proxy alone.
- Every client-supplied value is cut to a fixed length (login 255, user agent
  1024, address 64 characters), so a flood of oversized requests cannot bloat
  the table. Values are always shown as plain text, never as HTML.
- The failed attempts of today are counted in the timezone of the user
  looking at the form.
- No data leaves your server. There is no telemetry and no geolocation.

Part of the drkds Indian SME suite for Odoo 19 Community.
