# Knowledge Base (Lite)

Internal articles in a section tree, with rich text, tags and search.

A place to write down how your company actually does things, and a way to find
it again six months later.

## What it does

| Area | Behaviour |
|---|---|
| Sections | Nest freely; each carries its full path, e.g. `Handbook / Onboarding / First Week` |
| Articles | Rich text body, section, tags, author, last editor, draft or published, full chatter |
| Search | Searches the title, the article body and the tag names in one box |
| Browsing | Section tree in the sidebar with live counts; pick a branch, see everything below it |
| Filters | Section, tag, author, status, recency, unfiled, archived |
| Group by | Section, author, last editor, status, month of last change |
| Bookmarks | Per user, private, and stored separately so a read-only user can still use them |
| Views | Cards, list and a reading-oriented form, plus a Recently Updated list |

## Why the search works

An HTML body is pleasant to read and useless to search - a reader should not
have to know whether the word they want sits inside a `<strong>`. Every save
therefore stores a flattened plain text copy of the body in `body_text`, as a
stored computed field that can never drift from the source, and the search
looks there.

## Access

Two groups, under **Knowledge Base** in user settings:

- **Reader** — reads published articles, keeps personal bookmarks.
- **Editor** — writes articles, manages sections and tags, and is the only one
  who sees drafts.

Drafts are hidden from readers by a record rule, not by a hidden button.

## Installation

1. Copy this folder into your Odoo addons path.
2. Update the apps list.
3. Install **Knowledge Base (Lite)**.
4. Give each user a Knowledge Base group. Nobody sees the menu without one.

## Compatibility

Odoo 19 Community. Depends on `mail` only.

## Licence

LGPL-3.

The drkds Knowledge Base app adds article versioning with rollback, portal
sharing and approval workflows.

Part of the drkds Indian SME suite for Odoo 19 Community.
