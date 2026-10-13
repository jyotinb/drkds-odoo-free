# User manual - Login History

## 1. What this module tells you

Every time somebody tries to sign in to your Odoo, one line is written:
whether it worked, which login name was typed, when, from which IP address and
with which browser. Signing out writes a line too. With this you can answer:

- Who signed in today, and from where?
- Is somebody hammering an account with wrong passwords?
- Did a login name that does not exist get tried?
- When did a user last get in?

Odoo's built-in Devices list only shows sessions that succeeded. This module
also keeps the failures and the logouts.

## 2. Opening the screen

Settings > Users & Companies > Login History.

Only Settings administrators can see the menu or open the records. A regular
user who reaches the URL is refused.

## 3. Reading the list

| Column | Meaning |
| --- | --- |
| Date | When the event happened, shown in your timezone. |
| User | The user whose login name matched, archived users included. Empty when the name typed matches no user. |
| Login Typed | The login name exactly as entered, even when it was wrong. |
| Result | Success (green), 2FA Pending (orange), Failed (red) or Logout (blue). |
| IP Address | Where the request came from. Behind a reverse proxy, enable Odoo's proxy mode so this is the real client address. Empty for logins made over XML-RPC. |
| Browser, Operating System | Read from the browser string. Unusual clients show as Other; an empty string shows as Unknown. |
| User Agent, Session Hash | Hidden by default; enable them from the column chooser. |

Open a row to see everything on one form. Rows are read-only.

### Filters

- **Today**, **Last 7 Days**: by event date in your timezone.
- **Failed**, **Success**, **2FA Pending**, **Logout**: by result.
- **Unknown Login Name**: attempts whose login name matched no user.
- Group by User, Result, Day or IP Address.

### Graph

Switch to the graph view for a bar chart of events per day, stacked by
result. Combine it with the Failed filter to spot an attack at a glance.

### Two-factor logins

When a user has two-factor authentication, signing in takes two steps and the
list shows both:

| What happened | Rows |
| --- | --- |
| Right password, right code | 2FA Pending, then Success |
| Right password, wrong code | 2FA Pending, then Failed (one per wrong code) |
| Right password, page left without a code | 2FA Pending only |
| Right password from a browser remembered by 2FA | Success (no code is asked) |

A 2FA Pending row with no Success after it means somebody knew the password
but not the code: change that password.

### Integrations and API keys

A script or integration that signs in with `authenticate` (XML-RPC or
`/web/session/authenticate`) gets one row per sign-in, with a password or an
API key alike. The calls it makes afterwards with its API key are not
sign-ins and are not listed, so a busy integration does not fill the table.
Over XML-RPC, Odoo does not tell the module the caller's address or browser,
so those columns stay empty for such rows.

## 4. The user form

Settings > Users & Companies > Users, open any user. Administrators see a
**Login History** button at the top with two figures:

- **Failed Today**: failed attempts on this login name since midnight in your
  timezone.
- **Last Login**: date and time of the last successful login recorded by this
  module.

Click it to open that user's rows.

## 5. Keeping the table small

Settings > General Settings > Login History > **Keep Login History (days)**.

A scheduled action named *Login History: purge old records* runs once a day
and deletes rows older than this number of days. The default is 180. Enter 0
to keep everything. The action is listed under Settings > Technical >
Scheduled Actions if you want to run it by hand.

## 6. What is not recorded

- Nothing before the module was installed. Recording starts with the next
  login.
- Each call an integration makes with its API key after signing in (see
  above). A wrong key on such a call is refused by Odoo but not listed here.
- The country. No geolocation service is called, so the Country field on the
  form stays empty. This module makes no network call of any kind.
- The session identifier itself. Only a SHA-256 hash is stored, enough to
  tell two events of one session apart, useless to hijack it. Odoo changes
  the identifier when a login succeeds, so the success row and the logout row
  of one visit carry different hashes.
- Password values, right or wrong. Never.

## 7. Behaviour you can rely on

- A failed login is written even though Odoo rolls back the failed request;
  the row goes through its own database connection.
- Login names are matched exactly as Odoo matches them: `ADMIN` or a name
  with extra spaces is not the user `admin`, and is listed with an empty User.
- After 5 failures from one address (Odoo's default), Odoo refuses further
  attempts for a minute without checking them. Each refused attempt is still
  listed as Failed.
- Very long values sent by a client are cut: the login name to 255
  characters, the browser string to 1024, the address to 64. Everything is
  shown as plain text.
- Recording never blocks a login. If the row cannot be written, a warning is
  put in the server log and the user still gets in.
- Deleting a user keeps their rows; the User column simply becomes empty
  while Login Typed still shows the name.

Part of the drkds Indian SME suite for Odoo 19 Community.
