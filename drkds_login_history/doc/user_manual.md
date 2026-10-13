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
| User | The user whose login name matched. Empty when the name typed matches no user. |
| Login Typed | The login name exactly as entered, even when it was wrong. |
| Result | Success (green), Failed (red) or Logout (blue). |
| IP Address | Where the request came from. Behind a reverse proxy, enable Odoo's proxy mode so this is the real client address. |
| Browser, Operating System | Read from the browser string. Unusual clients show as Other; an empty string shows as Unknown. |
| User Agent, Session Hash | Hidden by default; enable them from the column chooser. |

Open a row to see everything on one form. Rows are read-only.

### Filters

- **Today**, **Last 7 Days**: by event date in your timezone.
- **Failed**, **Success**, **Logout**: by result.
- **Unknown Login Name**: attempts whose login name matched no user.
- Group by User, Result, Day or IP Address.

### Graph

Switch to the graph view for a bar chart of events per day, stacked by
result. Combine it with the Failed filter to spot an attack at a glance.

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
- Recording never blocks a login. If the row cannot be written, a warning is
  put in the server log and the user still gets in.
- Deleting a user keeps their rows; the User column simply becomes empty
  while Login Typed still shows the name.

Part of the drkds Indian SME suite for Odoo 19 Community.
