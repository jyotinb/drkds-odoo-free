# Changelog

## 19.0.1.0.0 - 2026-09-15

First release.

- Section hierarchy with materialised `parent_path`, computed full path,
  sibling ordering and a cycle guard.
- Articles with rich text body, section, tags, author, last editor, draft or
  published status, and chatter.
- Full text search across title, article body and tag names, backed by a stored
  plain text copy of the body.
- Section tree search panel with counters, plus filters and group-bys for
  section, tag, author, last editor, status and recency.
- Per-user bookmarks on a separate model, so read-only users can bookmark.
- Recently Updated and My Bookmarks views.
- Reader and Editor groups with record rules hiding drafts from readers.
