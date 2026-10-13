# Changelog

## 19.0.1.0.0 - 2026-10-13

First release.

- `drkds.login.record`: one row per login success, failure or logout, with
  the typed login, user, time, IP address, user agent, parsed browser and
  operating system, and a SHA-256 hash of the session identifier.
- Hooks on `res.users._login` and `/web/session/logout`; rows are written
  through a separate cursor so a failed login is still recorded.
- Login History menu under Settings > Users & Companies with list, graph and
  form views; smart button on the user form (failed attempts today, last
  successful login).
- Daily purge of rows older than the *Keep Login History (days)* setting
  (default 180, 0 keeps everything).
- Administrator-only access (`base.group_system`).
