# Changelog

## 19.0.1.0.0 - 2026-10-13

First release.

- `drkds.login.record`: one row per login success, 2FA pending, failure or
  logout, with the typed login, user, time, IP address, user agent, parsed
  browser and operating system, and a SHA-256 hash of the session identifier.
- Hooks on `res.users._login`, the second-factor check of a login,
  `/web/session/logout` and `/web/session/destroy`; rows are written through
  a separate cursor so a failed login is still recorded.
- Login History menu under Settings > Users & Companies with list, graph and
  form views; smart buttons on the user form (last successful login, failed
  attempts today).
- Daily purge of rows older than the *Keep Login History (days)* setting
  (default 180, 0 keeps everything).
- Administrator-only access (`base.group_system`).

### Fixed during review, before release

- Two-factor logins: a right password was recorded as **Success** although
  the user was not signed in until the 2FA code was accepted, and the code
  step itself was never recorded. The password step is now **2FA Pending**
  (new result), the code step writes its own Success or Failed row, and a
  browser remembered by 2FA is a plain Success.
- The *Failed Attempts Today* and *Last Successful Login* figures on users
  were computed in sudo without a group, so any internal user could read any
  account's figures over RPC. Both fields now require `base.group_system`.
- A failed attempt on an archived user was listed with an empty User, as an
  unknown login name. Archived users are now matched.
- The user agent, the address (with proxy mode, taken from
  `X-Forwarded-For`) and the login were stored at any length; a client could
  write tens of kilobytes per failed attempt. They are now cut to 1024, 64
  and 255 characters.
- A JSON-RPC login sent as a number made the module raise a TypeError in
  place of Odoo's Access Denied, and the attempt was not recorded. Recording
  now never raises, whatever the login's type.
- A passkey login was recorded without its login name, read before
  `auth_passkey` fills it in. It is now read after.
- `/web/session/destroy`, the JSON-RPC logout, wrote no Logout row.
- The *Last 7 Days* filter started at midnight UTC and *Today* used the
  browser's timezone; both now use the user's timezone, like the figures on
  the user form.
- Documented which logins are recorded and which are not: API-key calls after
  `authenticate`, XML-RPC rows without address, Odoo's login cooldown.
- The user form showed both figures in one button, where they ran together
  ("Failed TodayLast Login") with the values squeezed underneath. Each figure
  now has its own button: *Last Login* opens the user's rows, *Failed Today*
  opens that user's failed attempts of today.
