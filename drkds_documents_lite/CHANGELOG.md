# Changelog

## 19.0.1.0.0 - 2026-10-13

First release.

- Folder tree with full path, sequence, company, read groups, write groups
  and an optional mirrored model; sub-folders inherit the parent's groups.
  Two folders seeded: Company Documents and Linked Records.
- Documents with name, folder, file stored as an ir.attachment, tags, owner,
  contact, linked record, description, expiry date; type and size read from
  the file; chatter, activities and field tracking.
- Kanban with image thumbnails and file-type icons, list, form with inline
  PDF or image preview and Download and Open Record buttons, activity view,
  search with filters and group-bys, Documents and Expiring menus.
- Add to Documents server action on attachment lists, with a folder and tag
  wizard; files are linked, never copied or filed twice.
- Chatter mirroring for the models picked in Settings, into a folder per
  model under Linked Records.
- Daily expiry job scheduling a to-do for the owner seven days ahead, once
  per expiry date.
- Document user and manager groups, record rules from folder groups and
  multi-company rules.
- Uninstall keeps every file: uploaded files become plain attachments,
  mirrored files stay on their records.
