# Knowledge Base (Lite) — user manual

## 1. Before you start

Install the module, then give every user a group. The menu is invisible without
one.

Go to **Settings → Users & Companies → Users**, open a user, and under
**Knowledge Base** choose:

- **Reader** — can read published articles and keep bookmarks.
- **Editor** — everything a reader can do, plus writing articles, managing
  sections and tags, and seeing drafts.

## 2. Build the shelves first

**Knowledge Base → Configuration → Sections**.

Create the top-level sections first (Handbook, Engineering, Finance), then open
one and add sub-sections on the **Sub-sections** tab. The **Full Path** field
shows where a section really sits.

A section cannot be moved inside one of its own sub-sections. The save is
refused with a message rather than silently corrupting the tree.

Use **Description** for a one-line note on what belongs in the section. Future
authors will thank you.

## 3. Write an article

**Knowledge Base → Articles → New**.

- **Title** — write the question a reader would ask, not a filing code.
- Under the title, set the **section**, check the **author**, and add **tags**.
- Write the body. Use headings for anything longer than a screen; the reading
  view styles them so a reader can skim.
- Save. The article is a **Draft**: only editors can see it.
- Press **Publish** when it is ready. The publication date is stamped
  automatically.

**Back to Draft** hides it again — useful when a policy is under revision.

The **Last Edited By** stamp updates by itself whenever the title, body,
section, tags or status change.

## 4. Find things again

The **Articles** view opens on published articles, newest change first.

- **Search box** — searches the title, the article text and the tag names at
  once. A word that appears only in the middle of an article will be found.
- **Title Only** / **Body Only** — pick one from the search dropdown when you
  want to be precise.
- **Section tree** on the left — click a branch to see everything below it,
  including articles filed in its sub-sections. The numbers are live.
- **Tags** in the same panel — tick several to narrow further.
- **Filters** — My Bookmarks, My Articles, Published, Draft, Updated This Month,
  Unfiled, Archived.
- **Group By** — Section, Author, Last Editor, Status, Last Updated.

**Recently Updated** is the "what changed while I was away" list.

## 5. Bookmarks

Click the bookmark star on a card, in the list, or on the article form. The
article appears under **My Bookmarks**.

Bookmarks are private. Nobody else sees yours, and yours are not affected by
anyone else's. You can bookmark an article you have no permission to edit.

## 6. Housekeeping

- Archive an article rather than deleting it when it is merely obsolete; the
  **Archived** filter brings it back.
- **Unfiled** lists articles with no section. Keep it empty.
- Tags are managed at **Configuration → Tags**, where you can also set a colour.

## 7. Good practice

- One question, one article. Two loosely related answers in one article are
  found by nobody.
- Put the answer in the first paragraph and the reasoning after it.
- Prefer a deeper section tree over long article titles.
- Re-read the Recently Updated list once a month.

## Licence

LGPL-3.

The drkds Knowledge Base app adds article versioning with rollback, portal
sharing and approval workflows.

Part of the drkds Indian SME suite for Odoo 19 Community.
